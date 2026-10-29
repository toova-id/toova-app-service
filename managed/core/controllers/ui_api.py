# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re
import unicodedata
from datetime import datetime

from lxml import etree

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

from odoo.addons.web.controllers.utils import clean_action


_FIELD_ATTRIBUTES = (
    'currency_field', 'digits', 'help', 'readonly', 'relation', 'required',
    'selection', 'sortable', 'string', 'type',
)


def _error(message, code='invalid_request', status=400):
    return request.make_json_response(
        {'error': {'code': code, 'message': str(message)}},
        status=status,
        headers=[('Cache-Control', 'no-store')],
    )


def _json_body():
    payload = request.params.get('payload')
    if not payload:
        return {}
    try:
        value = json.loads(payload)
    except (TypeError, ValueError) as error:
        raise ValidationError('Invalid JSON payload.') from error
    if not isinstance(value, dict):
        raise ValidationError('Payload must be an object.')
    return value


def _slug(value):
    normalized = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', normalized).strip('-') or 'menu'


def _managed_permission(key, level='read'):
    return not key or not hasattr(request.env.user, '_managed_has_permission') or request.env.user._managed_has_permission(key, level)

def _action_permission(action):
    return request.env[action.res_model]._managed_action_permission(_action_xmlid(action))

def _managed_action_ids(action_model=None):
    """Return explicit managed action anchors, never every installed Odoo action."""
    action_ids = set()
    for xmlid in request.env['managed.settings.registry']._managed_registry()['actions']:
        action = request.env.ref(xmlid, raise_if_not_found=False)
        if action and (action_model is None or action._name == action_model):
            action_ids.add(action.id)
    return action_ids


def _menu_tree():
    menus = request.env['ir.ui.menu'].load_web_menus(request.session.debug)
    managed_actions = {
        'ir.actions.act_window': _managed_action_ids('ir.actions.act_window'),
        'ir.actions.client': _managed_action_ids('ir.actions.client'),
    }
    hidden_xmlids = {
        'base.menu_management', 'base.menu_administration',
        'settings.menu_company_profile', 'settings.menu_users', 'settings.menu_roles',
    }

    def serialize_many(menu_ids, parent_path='/app'):
        items = []
        used = set()
        for menu_id in menu_ids:
            menu = menus.get(menu_id)
            permission = request.env['base']._managed_menu_permission((menu or {}).get('xmlid'))
            if not menu or menu.get('xmlid') in hidden_xmlids or permission and not _managed_permission(permission):
                continue
            slug = _slug(menu['name'])
            if slug in used:
                slug = f'{slug}-{menu_id:x}'
            used.add(slug)
            menu_path = f'{parent_path}/{slug}'
            children = serialize_many(menu['children'], menu_path)
            action_model = menu.get('actionModel')
            action_id = menu.get('actionID') if menu.get('actionID') in managed_actions.get(action_model, set()) else None
            if not action_id and not children:
                continue
            items.append({
                'id': menu['id'],
                'label': menu['name'],
                'path': menu_path if action_id else None,
                'actionId': action_id,
                'actionModel': action_model if action_id else None,
                'xmlid': menu.get('xmlid') or '',
                'module': menu.get('xmlid', '').partition('.')[0] or None,
                'children': children,
            })
        return items

    return serialize_many(menus['root']['children'])


def _visible_action_ids(action_model):
    return _managed_action_ids(action_model)


def _visible_action(action_id):
    try:
        action_id = int(action_id)
    except (TypeError, ValueError) as error:
        raise MissingError('Action not found.') from error
    if action_id not in _visible_action_ids('ir.actions.act_window'):
        raise AccessError('Action is not available for this user.')
    action = request.env['ir.actions.act_window'].sudo().browse(action_id).exists()
    if not action:
        raise MissingError('Action not found.')
    request.env[action.res_model].check_access_rights('read')
    if not _managed_permission(_action_permission(action)):
        raise AccessError('Action is not available for this user.')
    return action


def _action_xmlid(action):
    return action.get_external_id().get(action.id) or ''

def _scoped_record(action, record_id):
    context, domain = _eval_action(action)
    record = request.env[action.res_model].with_context(**context).search(
        expression.AND([domain, [('id', '=', record_id)]]), limit=1,
    )
    if not record:
        raise MissingError('Record not found.')
    return record

def _domain_value(value):
    if isinstance(value, (list, tuple)):
        return value[0] if value else False
    return value

def _relation_domain(field, parent_values):
    domain = []
    if field['name'] == 'state_id' and field.get('relation') == 'res.country.state':
        country_id = _domain_value(parent_values.get('country_id'))
        return [('country_id', '=', country_id)] if country_id else []
    if field['name'] == 'parent_id' and field.get('relation') == 'product.category':
        category_id = _domain_value(parent_values.get('__parent_id'))
        return [('id', 'not child_of', category_id)] if category_id else []
    if field['name'] == 'uom_po_id' and field.get('relation') == 'uom.uom':
        uom_id = _domain_value(parent_values.get('uom_id'))
        category = request.env['uom.uom'].browse(uom_id).category_id if uom_id else False
        return [('category_id', '=', category.id)] if category else []
    if field.get('relation') == 'res.partner' and field.get('parent') == 'seller_ids':
        return [('supplier_rank', '>', 0), ('is_company', '=', True), ('active', '=', True)]
    if field.get('relation') == 'product.product' and field.get('parent') == 'seller_ids':
        template_id = _domain_value(parent_values.get('__parent_id'))
        return [('product_tmpl_id', '=', template_id)] if template_id else [('id', '=', 0)]
    if field.get('relation') == 'product.attribute.value' and field.get('parent') == 'attribute_line_ids':
        attribute_id = _domain_value(parent_values.get('attribute_id'))
        return [('attribute_id', '=', attribute_id)] if attribute_id else [('id', '=', 0)]
    if field.get('relation') == 'product.product' and field.get('parent') == 'item_ids':
        template_id = _domain_value(parent_values.get('product_tmpl_id'))
        return [('product_tmpl_id', '=', template_id)] if template_id else [('id', '=', 0)]
    if field.get('relation') == 'product.pricelist' and field.get('parent') == 'item_ids':
        parent_id = _domain_value(parent_values.get('__parent_id'))
        return [('id', '!=', parent_id)] if parent_id else []
    if field.get('widget') == 'managed_customer_many2one' and field.get('relation') == 'res.partner':
        return [
            ('parent_id', '=', False),
            ('managed_role_ids.role', '=', 'customer'),
            ('managed_role_ids.company_id', '=', request.env.company.id),
            ('managed_role_ids.active', '=', True),
            ('active', '=', True),
        ]
    if field.get('widget') == 'managed_order_address_many2one' and field.get('relation') == 'res.partner':
        partner_id = _domain_value(parent_values.get('partner_id'))
        return [('id', 'child_of', partner_id), ('active', '=', True)] if partner_id else [('id', '=', 0)]
    if field.get('widget') == 'managed_order_pricelist_many2one' and field.get('relation') == 'product.pricelist':
        company_id = _domain_value(parent_values.get('company_id')) or request.env.company.id
        return [('active', '=', True), ('company_id', 'in', [False, company_id])]
    if field.get('widget') == 'managed_order_payment_term_many2one' and field.get('relation') == 'account.payment.term':
        company_id = _domain_value(parent_values.get('company_id')) or request.env.company.id
        return [('company_id', 'in', [False, company_id])]
    if field.get('widget') == 'managed_order_fiscal_position_many2one' and field.get('relation') == 'account.fiscal.position':
        company_id = _domain_value(parent_values.get('company_id')) or request.env.company.id
        return [('company_id', '=', company_id)]
    if field.get('widget') == 'managed_order_warehouse_many2one' and field.get('relation') == 'stock.warehouse':
        company_id = _domain_value(parent_values.get('company_id')) or request.env.company.id
        return [('company_id', '=', company_id), ('active', '=', True)]
    if field.get('widget') == 'managed_sale_product_many2one' and field.get('relation') == 'product.product':
        company_id = _domain_value(parent_values.get('company_id')) or request.env.company.id
        return [('sale_ok', '=', True), ('active', '=', True), ('product_tmpl_id.company_id', 'in', [False, company_id])]
    if field.get('widget') == 'managed_sale_uom_many2one' and field.get('relation') == 'uom.uom':
        product_id = _domain_value(parent_values.get('product_id'))
        product = request.env['product.product'].browse(product_id).exists() if product_id else request.env['product.product']
        return [('category_id', '=', product.uom_id.category_id.id)] if product else [('id', '=', 0)]
    if field.get('widget') == 'managed_stock_lot_many2one' and field.get('relation') == 'stock.lot':
        product_id = _domain_value(parent_values.get('product_id'))
        company_id = _domain_value(parent_values.get('company_id')) or request.env.company.id
        return [('product_id', '=', product_id), ('company_id', '=', company_id)] if product_id else [('id', '=', 0)]
    if field.get('relation') != 'managed.indonesia.region':
        return domain
    mapping = {
        'indonesia_regency_id': ('state_id', 'state_id', 'regency'),
        'indonesia_district_id': ('parent_id', 'indonesia_regency_id', 'district'),
        'indonesia_village_id': ('parent_id', 'indonesia_district_id', 'village'),
        'managed_indonesia_regency_id': ('state_id', 'state_id', 'regency'),
        'managed_indonesia_district_id': ('parent_id', 'managed_indonesia_regency_id', 'district'),
        'managed_indonesia_village_id': ('parent_id', 'managed_indonesia_district_id', 'village'),
    }
    target, parent_name, level = mapping.get(field['name'], (None, None, None))
    if level:
        domain.append(('level', '=', level))
        parent_id = _domain_value(parent_values.get(parent_name))
        domain.append((target, '=', parent_id or 0))
    return domain

def _eval_action(action):
    eval_context = request.env['ir.actions.actions']._get_eval_context(action)
    eval_context['context_today'] = datetime.now
    context = safe_eval(action.context or '{}', eval_context)
    domain = safe_eval(action.domain or '[]', eval_context)
    if not isinstance(context, dict) or not isinstance(domain, (list, tuple)):
        raise ValidationError('Invalid action context or domain.')
    context = {**context, 'managed_ui': True}
    model = request.env[action.res_model].with_context(**context)
    role = context.get('managed_party_role')
    if role and hasattr(model, '_managed_role_domain'):
        domain = expression.AND([list(domain), model._managed_role_domain(role)])
    if role == 'contact' and hasattr(model, '_managed_contact_domain'):
        domain = expression.AND([list(domain), model._managed_contact_domain()])
    return context, list(domain)


def _views(action, context):
    views = []
    for view_id, view_type in action.views:
        view_type = 'list' if view_type == 'tree' else view_type
        if view_type in ('list', 'form', 'search') and view_type not in {item[1] for item in views}:
            views.append([view_id or False, view_type])
    for view_type in ('list', 'form', 'search'):
        if view_type not in {item[1] for item in views}:
            views.append([False, view_type])
    model = request.env[action.res_model].with_context(**context)
    return model.get_views(views, {'action_id': action.id, 'load_filters': True, 'toolbar': True})


def _relation_view_schema(node, field):
    relation = field.get('relation')
    if not relation:
        return None
    tree = next((child for child in node if child.tag == 'tree'), None)
    if tree is None:
        return None
    relation_fields = request.env[relation].fields_get(attributes=_FIELD_ATTRIBUTES)
    columns = []
    seen = set()
    for child in tree.xpath('./field[@name]'):
        name = child.get('name')
        modifiers = json.loads(child.get('modifiers', '{}'))
        if name in seen or modifiers.get('column_invisible') is True or modifiers.get('invisible') is True:
            continue
        seen.add(name)
        meta = {key: relation_fields.get(name, {}).get(key) for key in _FIELD_ATTRIBUTES if key in relation_fields.get(name, {})}
        meta.update({
            'name': name,
            'label': child.get('string') or meta.get('string') or name.replace('_', ' ').title(),
            'widget': child.get('widget'),
            'placeholder': child.get('placeholder'),
            'parent': node.get('name'),
            'modifiers': modifiers,
        })
        columns.append(meta)
    return {
        'editable': bool(tree.get('editable')),
        'columns': columns,
    }


def _field_meta(metadata, node):
    name = node.get('name')
    field = dict(metadata.get(name, {}))
    field = {key: field.get(key) for key in _FIELD_ATTRIBUTES if key in field}
    field.update({
        'name': name,
        'label': node.get('string') or field.get('string') or name.replace('_', ' ').title(),
        'widget': node.get('widget'),
        'optional': node.get('optional'),
        'placeholder': node.get('placeholder'),
        'relationView': _relation_view_schema(node, field) if field.get('type') in ('one2many', 'many2many') else None,
    })
    options = node.get('options')
    if options:
        try:
            field['options'] = safe_eval(options)
        except Exception:
            field['options'] = {}
    modifiers = node.get('modifiers')
    if modifiers:
        try:
            field['modifiers'] = json.loads(modifiers)
        except ValueError:
            pass
    return field


def _contract_field(metadata, item, parent=None):
    config = {'name': item} if isinstance(item, str) else dict(item)
    name = config.pop('name', None)
    if not name or name not in metadata:
        raise ValidationError(f'Invalid managed UI field: {name}.')
    relation_config = config.pop('relation', None)
    selection = config.pop('selection', None)
    help_text = config.pop('help', None)
    field = {key: metadata[name].get(key) for key in _FIELD_ATTRIBUTES if key in metadata[name]}
    field.update({
        'name': name,
        'label': config.pop('label', None) or field.get('string') or name.replace('_', ' ').title(),
        'widget': config.pop('widget', None),
        'placeholder': config.pop('placeholder', None),
        'parent': parent,
        'modifiers': config.pop('modifiers', {}),
        'relationView': None,
    })
    if selection is not None:
        if field.get('type') != 'selection' or not isinstance(selection, (list, tuple)):
            raise ValidationError(f'Invalid selection override for field {name}.')
        field['selection'] = selection
    if help_text is not None:
        field['help'] = help_text
    if config:
        raise ValidationError(f'Unsupported managed UI field options: {", ".join(config)}.')
    if relation_config:
        relation = field.get('relation')
        if not relation or field.get('type') not in ('one2many', 'many2many'):
            raise ValidationError(f'Field {name} does not support relation columns.')
        relation_metadata = request.env[relation].fields_get(attributes=_FIELD_ATTRIBUTES)
        columns = [
            _contract_field(relation_metadata, column, parent=name)
            for column in relation_config.get('columns', [])
            if (column if isinstance(column, str) else column.get('name')) != 'company_id'
        ]
        relation_model = request.env[relation]
        relation_fields = [relation_model._fields[column['name']] for column in columns]
        inverse_field = relation_config.get('inverse_field')
        if inverse_field and inverse_field not in relation_metadata:
            raise ValidationError(f'Invalid inverse field: {inverse_field}.')
        field['relationView'] = {
            'editable': bool(relation_config.get('editable')),
            'inverseField': inverse_field,
            'onchange': {
                column.name: '1' if relation_model._has_onchange(column, relation_fields) else ''
                for column in relation_fields
            },
            'columns': columns,
        }
    return field

def _managed_view_schema(action):
    model = request.env[action.res_model]
    contract_getter = getattr(model, '_managed_ui_contract', None)
    if not contract_getter:
        return None
    action_xmlid = _action_xmlid(action)
    contract = contract_getter(action_xmlid)
    if not contract:
        return None
    context, domain = _eval_action(action)
    metadata = model.fields_get(attributes=_FIELD_ATTRIBUTES)
    list_contract = contract.get('list', {})
    form_contract = contract.get('form', {})
    columns = [_contract_field(metadata, field) for field in list_contract.get('fields', [])]
    form_fields = [_contract_field(metadata, field) for field in form_contract.get('fields', [])]
    if model._fields.get('company_id') and model._fields['company_id'].type == 'many2one' and model._fields['company_id'].comodel_name == 'res.company':
        form_fields = [field for field in form_fields if field['name'] != 'company_id']
    write_fields = list(form_contract.get('write_fields', [field['name'] for field in form_fields]))
    write_fields = [name for name in write_fields if name != 'company_id']
    if set(write_fields) - {field['name'] for field in form_fields}:
        raise ValidationError('Managed UI contract contains invalid write fields.')
    read_fields = list(dict.fromkeys(
        [field['name'] for field in columns] + list(list_contract.get('read_fields', []))
    ))
    if set(read_fields) - metadata.keys():
        raise ValidationError('Managed UI contract contains invalid read fields.')
    status_name = form_contract.get('status_field')
    status_field = next((field for field in form_fields if field['name'] == status_name), None)
    onchange_fields = [model._fields[field['name']] for field in form_fields]
    onchange = {
        field.name: '1'
        for field in onchange_fields
        if model._has_onchange(field, onchange_fields)
    }
    permission_key = model._managed_action_permission(action_xmlid)
    can_write = _managed_permission(permission_key, 'write')
    return {
        'id': action.id,
        'actionXmlid': action_xmlid,
        'schemaSource': 'managed',
        'name': action.name,
        'model': action.res_model,
        'domain': domain,
        'context': context,
        'limit': action.limit or 80,
        'list': {
            'id': False,
            'title': list_contract.get('title') or action.name,
            'columns': columns,
            'readFields': read_fields,
            'defaultOrder': list_contract.get('default_order') or model._order,
            'create': can_write and list_contract.get('create', model.check_access_rights('create', raise_exception=False)) and context.get('create', True) is not False,
            'delete': can_write and list_contract.get('delete', model.check_access_rights('unlink', raise_exception=False)),
            'export': request.env.user.has_group('base.group_allow_export'),
            'filters': list_contract.get('filters', []),
            'actions': [],
        },
        'form': {
            'id': False,
            'title': form_contract.get('title') or action.name,
            'sections': [{'label': 'Informasi utama', 'fields': form_fields}],
            'allFields': form_fields,
            'writeFields': write_fields,
            'create': can_write and form_contract.get('create', model.check_access_rights('create', raise_exception=False)) and context.get('create', True) is not False,
            'write': can_write and form_contract.get('write', model.check_access_rights('write', raise_exception=False)),
            'onchange': onchange,
            'statusField': status_field,
            'statusVisible': form_contract.get('status_visible', []),
            'buttons': form_contract.get('buttons', []),
        },
    }

def _view_schema(action):
    managed_schema = _managed_view_schema(action)
    if managed_schema:
        return managed_schema
    context, domain = _eval_action(action)
    views = _views(action, context)
    metadata = views['models'][action.res_model]

    list_view = views['views']['list']
    list_root = etree.fromstring(list_view['arch'])
    columns = []
    seen = set()
    for node in list_root.xpath('.//field[@name]'):
        if next(iter(node.iterancestors('field')), None) is not None:
            continue
        name = node.get('name')
        modifiers = json.loads(node.get('modifiers', '{}'))
        if name in seen or modifiers.get('column_invisible') is True or modifiers.get('invisible') is True:
            continue
        seen.add(name)
        columns.append(_field_meta(metadata, node))

    search_view = views['views']['search']
    search_root = etree.fromstring(search_view['arch'])
    filters = []
    eval_context = request.env['ir.actions.actions']._get_eval_context(action)
    eval_context['context_today'] = datetime.now
    for node in search_root.xpath('.//filter[@domain and @string]'):
        modifiers = json.loads(node.get('modifiers', '{}'))
        if modifiers.get('invisible') is True or node.get('context') and 'group_by' in node.get('context'):
            continue
        try:
            filter_domain = safe_eval(node.get('domain'), eval_context)
        except Exception:
            continue
        if isinstance(filter_domain, (list, tuple)):
            filters.append({
                'name': node.get('name') or f'filter_{len(filters)}',
                'label': node.get('string'),
                'domain': list(filter_domain),
            })

    toolbar = list_view.get('toolbar', {})
    bulk_actions = [
        {'id': item['id'], 'label': item['name'], 'kind': kind}
        for kind in ('action', 'print')
        for item in toolbar.get(kind, [])
    ]

    form_view = views['views']['form']
    form_root = etree.fromstring(form_view['arch'])
    sections = []
    section_map = {}
    form_onchange = {}
    status_field = None
    status_visible = []
    seen = set()
    for node in form_root.xpath('.//field[@name]'):
        if next(iter(node.iterancestors('field')), None) is not None:
            continue
        name = node.get('name')
        modifiers = json.loads(node.get('modifiers', '{}'))
        if name in seen or modifiers.get('invisible') is True:
            continue
        seen.add(name)
        page = next(iter(node.iterancestors('page')), None)
        group = next(iter(node.iterancestors('group')), None)
        label = (
            page.get('string') if page is not None else
            group.get('string') if group is not None and group.get('string') else
            'Informasi utama'
        )
        key = label or 'Informasi utama'
        if key not in section_map:
            section_map[key] = {'label': key, 'fields': []}
            sections.append(section_map[key])
        field_meta = _field_meta(metadata, node)
        section_map[key]['fields'].append(field_meta)
        if node.get('on_change'):
            form_onchange[name] = node.get('on_change')
        if node.get('widget') == 'statusbar' and status_field is None:
            status_field = field_meta
            status_visible = [value for value in node.get('statusbar_visible', '').split(',') if value]

    form_buttons = []
    for node in form_root.xpath('.//header/button[@name][@type]'):
        modifiers = json.loads(node.get('modifiers', '{}'))
        if modifiers.get('invisible') is True or node.get('type') not in ('object', 'action'):
            continue
        form_buttons.append({
            'name': node.get('name'),
            'label': node.get('string') or node.get('name'),
            'type': node.get('type'),
            'primary': 'oe_highlight' in node.get('class', ''),
            'modifiers': modifiers,
        })

    return {
        'id': action.id,
        'actionXmlid': _action_xmlid(action),
        'schemaSource': 'xml',
        'name': action.name,
        'model': action.res_model,
        'domain': domain,
        'context': context,
        'limit': action.limit or 80,
        'list': {
            'id': list_view['id'],
            'title': list_root.get('string') or action.name,
            'columns': columns,
            'readFields': [field['name'] for field in columns],
            'defaultOrder': list_root.get('default_order'),
            'create': request.env[action.res_model].check_access_rights('create', raise_exception=False),
            'delete': request.env[action.res_model].check_access_rights('unlink', raise_exception=False),
            'export': request.env.user.has_group('base.group_allow_export'),
            'filters': filters,
            'actions': bulk_actions,
        },
        'form': {
            'id': form_view['id'],
            'title': form_root.get('string') or action.name,
            'sections': sections,
            'allFields': [field for section in sections for field in section['fields']],
            'writeFields': [field['name'] for section in sections for field in section['fields']],
            'create': request.env[action.res_model].check_access_rights('create', raise_exception=False),
            'write': request.env[action.res_model].check_access_rights('write', raise_exception=False),
            'onchange': form_onchange,
            'statusField': status_field,
            'statusVisible': status_visible,
            'buttons': form_buttons,
        },
    }


def _allowed_fields(schema, view_type):
    if view_type == 'list':
        return schema['list'].get('readFields') or [field['name'] for field in schema['list']['columns']]
    return [field['name'] for field in schema['form'].get('allFields', [])] or [
        field['name'] for section in schema['form']['sections'] for field in section['fields']
    ]


def _form_fields(schema):
    fields = schema['form'].get('allFields') or [
        field for section in schema['form']['sections'] for field in section['fields']
    ]
    return {field['name']: field for field in fields}


def _writable_form_fields(schema):
    return set(schema['form'].get('writeFields') or _form_fields(schema))


def _x2many_default_values(value):
    ids = []
    pending = []
    for item in value or []:
        if isinstance(item, int):
            ids.append(item)
        elif isinstance(item, (list, tuple)) and item:
            command = item[0]
            if command == 6:
                ids = list(item[2] or [])
            elif command == 4:
                ids.append(item[1])
            elif command == 1:
                ids.append(item[1])
            elif command == 0 and isinstance(item[2], dict):
                pending.append(item[2])
            elif command == 5:
                ids = []
    return ids, pending


def _serialize_form_values(model, values, schema):
    serialized = dict(values)
    for name, field in _form_fields(schema).items():
        relation_view = field.get('relationView')
        if field.get('type') not in ('one2many', 'many2many'):
            continue
        ids, pending = _x2many_default_values(values.get(name))
        relation = model._fields[name].comodel_name
        if relation_view:
            child_fields = [column['name'] for column in relation_view['columns']]
            records = request.env[relation].browse(ids)
            if field.get('widget') == 'contact_persons':
                records = records.filtered(lambda record: record.type == 'contact' and not record.employee)
            rows = records.read(child_fields)
            columns = {column['name']: column for column in relation_view['columns']}
            for row in rows:
                for child_name, child_field in columns.items():
                    if child_field.get('type') == 'many2many' and isinstance(row.get(child_name), list):
                        row[child_name] = request.env[child_field['relation']].browse(row[child_name]).name_get()
            serialized[name] = rows + pending
        else:
            serialized[name] = request.env[relation].browse(ids).name_get()
    return serialized


def _window_action(payload):
    if not isinstance(payload, dict) or payload.get('type') != 'ir.actions.act_window':
        raise ValidationError('Invalid window action.')
    model_name = payload.get('res_model')
    allowed_models = {
        'sale.advance.payment.inv', 'account.payment.register',
        'stock.immediate.transfer', 'stock.backorder.confirmation',
    }
    if model_name not in allowed_models or model_name not in request.env:
        raise AccessError('Dialog is not available.')
    request.env[model_name].check_access_rights('read')
    return payload


def _window_action_schema(payload):
    action = _window_action(payload)
    model = request.env[action['res_model']].with_context(**(action.get('context') if isinstance(action.get('context'), dict) else {}))
    view_id = next((view_id for view_id, view_type in action.get('views', []) if view_type == 'form'), False)
    view = model.get_view(view_id or None, 'form')
    root = etree.fromstring(view['arch'])
    metadata = model.fields_get(attributes=_FIELD_ATTRIBUTES)
    fields_schema = []
    seen = set()
    for node in root.xpath('.//field[@name]'):
        name = node.get('name')
        modifiers = json.loads(node.get('modifiers', '{}'))
        if name in seen or name not in metadata:
            continue
        seen.add(name)
        fields_schema.append(_field_meta(metadata, node))
    buttons = []
    for node in root.xpath('.//footer/button[@name][@type]'):
        buttons.append({
            'name': node.get('name'), 'label': node.get('string') or node.get('name'),
            'type': node.get('type'), 'primary': 'btn-primary' in node.get('class', '') or 'oe_highlight' in node.get('class', ''),
        })
    return action, model, {'title': root.get('string') or action.get('name') or 'Dialog', 'fields': fields_schema, 'buttons': buttons}


def _action_payload(result):
    if not isinstance(result, dict) or not result.get('type'):
        return result or False
    if result['type'] == 'ir.actions.act_window':
        action = dict(result)
        action.setdefault('views', [(False, action.get('view_mode', 'form').split(',')[0])])
        return clean_action(action, request.env)
    return result


def _normalize_form_values(values, schema):
    normalized = dict(values)
    for name, field in _form_fields(schema).items():
        relation_view = field.get('relationView')
        rows = normalized.get(name)
        if field.get('type') not in ('one2many', 'many2many') or not isinstance(rows, list):
            continue
        if not relation_view or not rows or not isinstance(rows[0], dict):
            normalized[name] = [(6, 0, [item[0] if isinstance(item, (list, tuple)) else item for item in rows])]
            continue
        columns = {column['name']: column for column in relation_view['columns']}
        allowed = {name for name, column in columns.items() if not column.get('readonly')}
        existing_ids = [row['id'] for row in rows if isinstance(row.get('id'), int) and row.get('active', True) is not False]
        if field.get('widget') in ('contact_persons', 'managed_bank_accounts', 'managed_supplier_prices', 'managed_attribute_lines', 'managed_variants', 'managed_attribute_values', 'managed_pricelist_rules', 'managed_uom_units', 'managed_stock_move_lines'):
            commands = []
        else:
            commands = [(6, 0, existing_ids)]
        for row in rows:
            if field.get('widget') in ('managed_supplier_prices', 'managed_attribute_values', 'managed_pricelist_rules') and row.get('active', True) is False:
                if isinstance(row.get('id'), int):
                    commands.append((2, row['id'], 0))
                continue
            data = {}
            for key in allowed & row.keys():
                value = row[key]
                column_type = columns[key].get('type')
                if column_type == 'many2one' and isinstance(value, (list, tuple)):
                    value = value[0] if value else False
                elif column_type == 'many2many' and isinstance(value, list):
                    value = [(6, 0, [item[0] if isinstance(item, (list, tuple)) else item for item in value])]
                data[key] = value
            if field.get('widget') == 'contact_persons':
                data.setdefault('type', 'contact')
            if field.get('widget') == 'managed_uom_units' and row.get('active', True) is False:
                data['active'] = False
            if isinstance(row.get('id'), int):
                commands.append((1, row['id'], data))
            else:
                commands.append((0, 0, data))
        normalized[name] = commands
    return normalized


class ManagedUiApi(http.Controller):

    @http.route('/api/v1/ui/navigation', type='http', auth='user', methods=['GET'])
    def navigation(self):
        return request.make_json_response({'items': _menu_tree()}, headers=[('Cache-Control', 'no-store')])

    @http.route('/api/v1/settings', type='http', auth='user', methods=['GET'])
    def settings_sections(self):
        try:
            registry = request.env['managed.settings.registry']._managed_registry()
            sections = []
            for section in registry['sections']:
                if not _managed_permission(section['permission']):
                    continue
                item = dict(section)
                provider = item.get('provider')
                action_xmlid = item.get('action_xmlid')
                action = request.env.ref(action_xmlid, raise_if_not_found=False) if action_xmlid else False
                item['actionId'] = action.id if action and action._name == 'ir.actions.act_window' else None
                item['level'] = request.env.user._managed_permission_level(item['permission'])
                item['readiness'] = request.env[provider].get_readiness() if provider and hasattr(request.env[provider], 'get_readiness') else {'status': 'ready', 'message': None}
                sections.append(item)
            features = [
                {**feature, 'permissions': [
                    {**permission, 'level': request.env.user._managed_permission_level(permission['key'])}
                    for permission in feature['permissions']
                ]}
                for feature in registry['features']
            ]
            return request.make_json_response({'sections': sections, 'features': features}, headers=[('Cache-Control', 'no-store')])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/settings/relations/<string:model_name>', type='http', auth='user', methods=['GET'])
    def settings_relation(self, model_name, q='', **kw):
        try:
            allowed = {'res.country', 'res.country.state', 'res.currency', 'product.category', 'uom.uom'}
            if model_name not in allowed or not any(_managed_permission(key) for key in ('settings.company', 'settings.products')):
                raise AccessError('Settings relation is not available.')
            model = request.env[model_name]
            model.check_access_rights('read')
            domain = []
            if model_name == 'res.country.state' and kw.get('countryId', '').isdigit():
                domain = [('country_id', '=', int(kw['countryId']))]
            records = model.name_search(q, args=domain, limit=20)
            return request.make_json_response({'items': [{'id': item_id, 'label': label} for item_id, label in records]})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/settings/<string:section_key>', type='http', auth='user', methods=['GET'])
    def settings_section(self, section_key):
        try:
            section = next((item for item in request.env['managed.settings.registry']._managed_registry()['sections'] if item['key'] == section_key), None)
            if not section or not section.get('provider'):
                raise MissingError('Settings section not found.')
            if not _managed_permission(section['permission']):
                raise AccessError('Settings section is not available.')
            provider = request.env[section['provider']]
            return request.make_json_response({'section': section, 'values': provider.get_values(), 'readiness': provider.get_readiness() if hasattr(provider, 'get_readiness') else {'status': 'ready'}})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/settings/<string:section_key>', type='http', auth='user', methods=['POST'])
    def save_settings_section(self, section_key):
        try:
            section = next((item for item in request.env['managed.settings.registry']._managed_registry()['sections'] if item['key'] == section_key), None)
            if not section or not section.get('provider'):
                raise MissingError('Settings section not found.')
            if not _managed_permission(section['permission'], 'write'):
                raise AccessError('Write access is not available for this settings section.')
            values = _json_body().get('values', {})
            if not isinstance(values, dict):
                raise ValidationError('Payload must contain field values.')
            with request.env.cr.savepoint():
                result = request.env[section['provider']].save_values(values)
            return request.make_json_response({'values': result})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/client-actions/<int:action_id>', type='http', auth='user', methods=['GET'])
    def client_action(self, action_id):
        try:
            if action_id not in _visible_action_ids('ir.actions.client'):
                raise AccessError('Action is not available for this user.')
            action = request.env['ir.actions.client'].sudo().browse(action_id).exists()
            if not action:
                raise MissingError('Action not found.')
            permission = request.env['base']._managed_action_permission(_action_xmlid(action))
            if not _managed_permission(permission):
                raise AccessError('Action is not available for this user.')
            return request.make_json_response({
                'id': action.id,
                'name': action.name,
                'tag': action.tag,
                'target': action.target,
                'params': action.params or {},
                'model': action.res_model,
            }, headers=[('Cache-Control', 'no-store')])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)

    @http.route('/api/v1/ui/window-action', type='http', auth='user', methods=['GET'])
    def window_action(self, payload=None):
        try:
            action, model, schema = _window_action_schema(json.loads(payload or '{}'))
            field_names = [field['name'] for field in schema['fields']]
            record = model.browse(action.get('res_id')).exists() if action.get('res_id') else model.new(model.default_get(field_names))
            values = record.read(field_names)[0] if record.id else record._convert_to_write(record._cache)
            values = {name: values.get(name, False) for name in field_names}
            return request.make_json_response({'schema': schema, 'values': values})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/window-action/run', type='http', auth='user', methods=['POST'])
    def run_window_action(self):
        try:
            payload = _json_body()
            action, model, schema = _window_action_schema(payload.get('action'))
            button_name = payload.get('name')
            button_type = payload.get('type')
            allowed = {(item['name'], item['type']) for item in schema['buttons']}
            if (button_name, button_type) not in allowed:
                raise AccessError('Button is not available.')
            allowed_fields = {field['name'] for field in schema['fields']}
            raw_values = payload.get('values', {})
            if not isinstance(raw_values, dict):
                raise ValidationError('Payload must contain field values.')
            values = {}
            for name, value in raw_values.items():
                if name not in allowed_fields or model._fields[name].readonly:
                    continue
                field = model._fields[name]
                if field.type == 'many2one' and isinstance(value, (list, tuple)):
                    value = value[0] if value else False
                elif field.type in ('one2many', 'many2many') and isinstance(value, list) and (not value or not isinstance(value[0], (list, tuple))):
                    value = [(6, 0, [item[0] if isinstance(item, (list, tuple)) else item for item in value])]
                values[name] = value
            with request.env.cr.savepoint():
                record = model.browse(action.get('res_id')).exists() if action.get('res_id') else model.create(values)
                if action.get('res_id') and values:
                    record.write(values)
                if button_type == 'object':
                    result = getattr(record, button_name)()
                else:
                    target = request.env['ir.actions.actions'].browse(int(button_name)).exists()
                    if not target:
                        raise MissingError('Action not found.')
                    result = request.env[target.type].browse(target.id).read()[0]
            return request.make_json_response({'result': _action_payload(result)})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (AttributeError, UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>', type='http', auth='user', methods=['GET'])
    def action(self, action_id):
        try:
            return request.make_json_response(_view_schema(_visible_action(action_id)), headers=[('Cache-Control', 'no-store')])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/records', type='http', auth='user', methods=['GET'])
    def records(self, action_id, page=1, q='', order=None, filters=None, ids=None, **kw):
        try:
            action = _visible_action(action_id)
            schema = _view_schema(action)
            context, domain = _eval_action(action)
            model = request.env[action.res_model].with_context(**context)
            if ids:
                try:
                    related_ids = [int(value) for value in ids.split(',') if value]
                except ValueError as error:
                    raise ValidationError('Invalid related record filter.') from error
                if not related_ids:
                    raise ValidationError('Invalid related record filter.')
                domain = expression.AND([domain, [('id', 'in', related_ids)]])
            page = max(int(page), 1)
            page_size = min(schema['limit'], 100)
            field_names = _allowed_fields(schema, 'list')
            searchable = [
                field['name'] for field in schema['list']['columns']
                if field.get('type') in ('char', 'text', 'many2one')
            ][:6]
            if q and searchable:
                domain = expression.AND([domain, expression.OR([[(name, 'ilike', q)] for name in searchable])])
            if filters:
                selected = set(filters.split(','))
                available = {item['name']: item['domain'] for item in schema['list']['filters']}
                if selected - available.keys():
                    raise ValidationError('Invalid filter.')
                domain = expression.AND([domain, *[available[name] for name in selected]])
            if order:
                order_field = order.removeprefix('-')
                sortable = {field['name'] for field in schema['list']['columns'] if field.get('sortable')}
                if order_field not in sortable:
                    raise ValidationError('Invalid sort field.')
                order = f"{order_field} {'desc' if order.startswith('-') else 'asc'}"
            else:
                order = schema['list']['defaultOrder'] or model._order
            result = model.web_search_read(
                domain, field_names, offset=(page - 1) * page_size,
                limit=page_size, order=order,
            )
            return request.make_json_response({
                'items': result['records'], 'total': result['length'],
                'page': page, 'pageSize': page_size,
            }, headers=[('Cache-Control', 'no-store')])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/records/<string:record_id>', type='http', auth='user', methods=['GET'])
    def record(self, action_id, record_id):
        try:
            action = _visible_action(action_id)
            schema = _view_schema(action)
            context, _domain = _eval_action(action)
            model = request.env[action.res_model].with_context(**context)
            fields_to_read = _allowed_fields(schema, 'form')
            if record_id == 'new':
                defaults = model._managed_apply_company_default(model.default_get(fields_to_read))
                values = _serialize_form_values(model, defaults, schema)
                return request.make_json_response({'id': None, 'values': values}, headers=[('Cache-Control', 'no-store')])
            record = _scoped_record(action, int(record_id))
            values = _serialize_form_values(model, record.read(fields_to_read)[0], schema)
            return request.make_json_response({'id': record.id, 'values': values}, headers=[('Cache-Control', 'no-store')])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/onchange', type='http', auth='user', methods=['POST'])
    def onchange(self, action_id):
        try:
            action = _visible_action(action_id)
            schema = _view_schema(action)
            payload = _json_body()
            values = payload.get('values', {})
            field_name = payload.get('field')
            if field_name not in schema['form']['onchange'] or not isinstance(values, dict):
                raise ValidationError('Invalid onchange request.')
            allowed = set(_allowed_fields(schema, 'form'))
            values = _normalize_form_values({name: value[0] if isinstance(value, (list, tuple)) and _form_fields(schema).get(name, {}).get('type') == 'many2one' and value else value for name, value in values.items() if name in allowed}, schema)
            spec = {name: onchange_spec for name, onchange_spec in schema['form']['onchange'].items()}
            context, _domain = _eval_action(action)
            model = request.env[action.res_model].with_context(**context)
            result = model.onchange(values, field_name, spec)
            return request.make_json_response({
                'values': result.get('value', {}),
                'warnings': result.get('warning') or result.get('warnings') or [],
                'domain': result.get('domain', {}),
            })
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/relations/<string:field_name>/onchange', type='http', auth='user', methods=['POST'])
    def relation_onchange(self, action_id, field_name):
        try:
            action = _visible_action(action_id)
            schema = _view_schema(action)
            field = _form_fields(schema).get(field_name)
            relation_view = (field or {}).get('relationView')
            payload = _json_body()
            values = payload.get('values', {})
            parent_values = payload.get('parentValues', {})
            changed_field = payload.get('field')
            onchange_spec = (relation_view or {}).get('onchange', {})
            columns = {column['name']: column for column in (relation_view or {}).get('columns', [])}
            if not relation_view or changed_field not in columns or not onchange_spec.get(changed_field) or not isinstance(values, dict) or not isinstance(parent_values, dict):
                raise ValidationError('Invalid relation onchange request.')
            relation_model = request.env[field['relation']]
            allowed = set(columns)
            line_values = {
                name: value[0] if isinstance(value, (list, tuple)) and columns[name].get('type') == 'many2one' and value else value
                for name, value in values.items() if name in allowed
            }
            inverse_field = relation_view.get('inverseField')
            if inverse_field:
                parent_allowed = set(_allowed_fields(schema, 'form'))
                parent = {
                    name: value[0] if isinstance(value, (list, tuple)) and _form_fields(schema).get(name, {}).get('type') == 'many2one' and value else value
                    for name, value in parent_values.items() if name in parent_allowed and name != field_name
                }
                line_values[inverse_field] = parent
            result = relation_model.with_context(**_eval_action(action)[0]).onchange(
                line_values, changed_field, onchange_spec,
            )
            changed = result.get('value', {})
            changed.pop(inverse_field, None)
            return request.make_json_response({
                'values': changed,
                'warnings': result.get('warning') or result.get('warnings') or [],
                'domain': result.get('domain', {}),
            })
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/records/<int:record_id>/button', type='http', auth='user', methods=['POST'])
    def form_button(self, action_id, record_id):
        try:
            action = _visible_action(action_id)
            if not _managed_permission(_action_permission(action), 'write'):
                raise AccessError('Write access is not available for this action.')
            schema = _view_schema(action)
            payload = _json_body()
            button_name = payload.get('name')
            button_type = payload.get('type')
            allowed = {(item['name'], item['type']) for item in schema['form']['buttons']}
            if (button_name, button_type) not in allowed:
                raise AccessError('Button is not available.')
            record = _scoped_record(action, record_id)
            if button_type == 'object':
                result = getattr(record, button_name)()
            else:
                target = request.env['ir.actions.actions'].browse(int(button_name)).exists()
                if not target:
                    raise MissingError('Action not found.')
                action_type = target.type
                result = request.env[action_type].browse(target.id).read()[0]
            _context, domain = _eval_action(action)
            record_available = bool(record.exists() and request.env[action.res_model].search_count(
                expression.AND([domain, [('id', '=', record_id)]]),
            ))
            return request.make_json_response({'result': _action_payload(result), 'recordAvailable': record_available})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (AttributeError, UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/records', type='http', auth='user', methods=['POST'])
    def create(self, action_id):
        try:
            action = _visible_action(action_id)
            if not _managed_permission(_action_permission(action), 'write'):
                raise AccessError('Write access is not available for this action.')
            schema = _view_schema(action)
            context, _domain = _eval_action(action)
            values = _json_body().get('values', {})
            allowed = _writable_form_fields(schema)
            if not isinstance(values, dict):
                raise ValidationError('Payload must contain field values.')
            values = {name: value for name, value in values.items() if name in allowed}
            values = {name: value[0] if isinstance(value, (list, tuple)) and _form_fields(schema).get(name, {}).get('type') == 'many2one' and value else value for name, value in values.items()}
            values = _normalize_form_values(values, schema)
            values = request.env[action.res_model].with_context(**context)._managed_apply_company_default(values)
            with request.env.cr.savepoint():
                record = request.env[action.res_model].with_context(**context).create(values)
            return request.make_json_response({'id': record.id}, status=201)
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/records/<int:record_id>', type='http', auth='user', methods=['POST'])
    def update(self, action_id, record_id):
        try:
            action = _visible_action(action_id)
            if not _managed_permission(_action_permission(action), 'write'):
                raise AccessError('Write access is not available for this action.')
            schema = _view_schema(action)
            context, _domain = _eval_action(action)
            values = _json_body().get('values', {})
            allowed = _writable_form_fields(schema)
            if not isinstance(values, dict):
                raise ValidationError('Payload must contain field values.')
            record = _scoped_record(action, record_id)
            values = {name: value for name, value in values.items() if name in allowed}
            values = {name: value[0] if isinstance(value, (list, tuple)) and _form_fields(schema).get(name, {}).get('type') == 'many2one' and value else value for name, value in values.items()}
            with request.env.cr.savepoint():
                record.write(_normalize_form_values(values, schema))
            return request.make_json_response({'id': record.id})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/records/delete', type='http', auth='user', methods=['POST'])
    def delete_records(self, action_id):
        try:
            action = _visible_action(action_id)
            if not _managed_permission(_action_permission(action), 'write'):
                raise AccessError('Write access is not available for this action.')
            schema = _view_schema(action)
            if not schema['list']['delete']:
                raise AccessError('Delete is not available for this action.')
            ids = _json_body().get('ids', [])
            if not isinstance(ids, list) or not ids or not all(isinstance(item, int) for item in ids):
                raise ValidationError('Select records to delete.')
            context, domain = _eval_action(action)
            model = request.env[action.res_model].with_context(**context)
            records = model.browse(ids).exists()
            if set(records.ids) != set(ids) or model.search_count(expression.AND([domain, [('id', 'in', ids)]])) != len(ids):
                raise AccessError('One or more records are unavailable.')
            with request.env.cr.savepoint():
                records.unlink()
            return request.make_json_response({'deleted': len(ids)})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/bulk-action', type='http', auth='user', methods=['POST'])
    def bulk_action(self, action_id):
        try:
            action = _visible_action(action_id)
            if not _managed_permission(_action_permission(action), 'write'):
                raise AccessError('Write access is not available for this action.')
            payload = _json_body()
            ids = payload.get('ids', [])
            server_action_id = payload.get('serverActionId')
            allowed = {item['id'] for item in _view_schema(action)['list']['actions'] if item['kind'] == 'action'}
            if server_action_id not in allowed or not isinstance(ids, list) or not ids:
                raise ValidationError('Invalid bulk action.')
            context, domain = _eval_action(action)
            records = request.env[action.res_model].with_context(**context).browse(ids).exists()
            if set(records.ids) != set(ids) or request.env[action.res_model].search_count(expression.AND([domain, [('id', 'in', ids)]])) != len(ids):
                raise AccessError('One or more records are unavailable.')
            result = request.env['ir.actions.server'].browse(server_action_id).with_context(
                active_model=action.res_model, active_ids=ids, active_id=ids[0], active_domain=domain,
            ).run()
            return request.make_json_response({'result': result or False})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/export.csv', type='http', auth='user', methods=['GET'])
    def export_csv(self, action_id, ids=None, q='', filters=None, **kw):
        try:
            if not request.env.user.has_group('base.group_allow_export'):
                raise AccessError('Export is not allowed.')
            action = _visible_action(action_id)
            schema = _view_schema(action)
            context, domain = _eval_action(action)
            model = request.env[action.res_model].with_context(**context)
            selected_ids = [int(value) for value in ids.split(',')] if ids else []
            if selected_ids:
                domain = expression.AND([domain, [('id', 'in', selected_ids)]])
            if filters:
                selected = set(filters.split(','))
                available = {item['name']: item['domain'] for item in schema['list']['filters']}
                if selected - available.keys():
                    raise ValidationError('Invalid filter.')
                domain = expression.AND([domain, *[available[name] for name in selected]])
            searchable = [field['name'] for field in schema['list']['columns'] if field.get('type') in ('char', 'text', 'many2one')][:6]
            if q and searchable:
                domain = expression.AND([domain, expression.OR([[(name, 'ilike', q)] for name in searchable])])
            field_names = _allowed_fields(schema, 'list')
            rows = model.search_read(domain, field_names, order=schema['list']['defaultOrder'] or model._order)
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([field['label'] for field in schema['list']['columns']])
            for row in rows:
                writer.writerow([
                    value[1] if isinstance(value := row.get(field['name']), (list, tuple)) and len(value) > 1 else value
                    for field in schema['list']['columns']
                ])
            filename = re.sub(r'[^a-zA-Z0-9_-]+', '-', action.name).strip('-').lower() or 'export'
            return request.make_response(output.getvalue(), [
                ('Content-Type', 'text/csv; charset=utf-8'),
                ('Content-Disposition', f'attachment; filename="{filename}.csv"'),
                ('Cache-Control', 'no-store'),
            ])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/relations/<string:field_name>', type='http', auth='user', methods=['GET'])
    def relation(self, action_id, field_name, q='', parent=None, values=None, **kw):
        try:
            action = _visible_action(action_id)
            schema = _view_schema(action)
            fields_by_name = _form_fields(schema)
            field = fields_by_name.get(field_name)
            if parent:
                parent_field = fields_by_name.get(parent)
                field = next((column for column in (parent_field or {}).get('relationView', {}).get('columns', []) if column['name'] == field_name), None)
            if not field or field.get('type') not in ('many2one', 'many2many') or not field.get('relation'):
                raise ValidationError('Invalid relation field.')
            relation_model = request.env[field['relation']]
            relation_model.check_access_rights('read')
            try:
                parent_values = json.loads(values or '{}')
                record_id = kw.get('recordId')
                if record_id and str(record_id).isdigit():
                    parent_values['__parent_id'] = int(record_id)
            except (TypeError, ValueError) as error:
                raise ValidationError('Invalid relation values.') from error
            if not isinstance(parent_values, dict):
                raise ValidationError('Invalid relation values.')
            records = relation_model.name_search(q, args=_relation_domain(field, parent_values), limit=20)
            return request.make_json_response({'items': [{'id': item_id, 'label': label} for item_id, label in records]})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

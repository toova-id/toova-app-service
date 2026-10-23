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

from .utils import clean_action


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


def _menu_tree():
    menus = request.env['ir.ui.menu'].load_web_menus(request.session.debug)
    hidden_xmlids = {'base.menu_management', 'base.menu_administration'}

    def serialize_many(menu_ids, parent_path='/app'):
        items = []
        used = set()
        for menu_id in menu_ids:
            menu = menus.get(menu_id)
            if not menu or menu.get('xmlid') in hidden_xmlids:
                continue
            slug = _slug(menu['name'])
            if slug in used:
                slug = f'{slug}-{menu_id:x}'
            used.add(slug)
            menu_path = f'{parent_path}/{slug}'
            children = serialize_many(menu['children'], menu_path)
            action_model = menu.get('actionModel')
            action_id = menu.get('actionID') if action_model in ('ir.actions.act_window', 'ir.actions.client') else None
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
    return {
        menu['actionID']
        for menu in request.env['ir.ui.menu'].load_web_menus(request.session.debug).values()
        if menu.get('actionModel') == action_model and menu.get('actionID')
        and menu.get('xmlid') not in {'base.menu_management', 'base.menu_administration'}
    }


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
    return action


def _eval_action(action):
    eval_context = request.env['ir.actions.actions']._get_eval_context(action)
    eval_context['context_today'] = datetime.now
    context = safe_eval(action.context or '{}', eval_context)
    domain = safe_eval(action.domain or '[]', eval_context)
    if not isinstance(context, dict) or not isinstance(domain, (list, tuple)):
        raise ValidationError('Invalid action context or domain.')
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


def _view_schema(action):
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
        'name': action.name,
        'model': action.res_model,
        'domain': domain,
        'context': context,
        'limit': action.limit or 80,
        'list': {
            'id': list_view['id'],
            'title': list_root.get('string') or action.name,
            'columns': columns,
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
        return [field['name'] for field in schema['list']['columns']]
    return [field['name'] for section in schema['form']['sections'] for field in section['fields']]


def _form_fields(schema):
    return {
        field['name']: field
        for section in schema['form']['sections']
        for field in section['fields']
    }


def _serialize_form_values(model, values, schema):
    serialized = dict(values)
    for name, field in _form_fields(schema).items():
        relation_view = field.get('relationView')
        if field.get('type') not in ('one2many', 'many2many'):
            continue
        ids = values.get(name) or []
        ids = [item[0] if isinstance(item, (list, tuple)) else item for item in ids]
        if not ids:
            serialized[name] = []
            continue
        relation = model._fields[name].comodel_name
        if relation_view:
            child_fields = [column['name'] for column in relation_view['columns']]
            serialized[name] = request.env[relation].browse(ids).read(child_fields)
        else:
            serialized[name] = request.env[relation].browse(ids).name_get()
    return serialized


def _window_action(payload):
    if not isinstance(payload, dict) or payload.get('type') != 'ir.actions.act_window':
        raise ValidationError('Invalid window action.')
    model_name = payload.get('res_model')
    if model_name not in request.env:
        raise ValidationError('Invalid action model.')
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
        if name in seen or modifiers.get('invisible') is True or name not in metadata:
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
        allowed = {column['name'] for column in relation_view['columns']}
        existing_ids = [row['id'] for row in rows if isinstance(row.get('id'), int)]
        commands = [(6, 0, existing_ids)]
        for row in rows:
            data = {key: value[0] if isinstance(value := row.get(key), (list, tuple)) and value else value for key in allowed if key in row}
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

    @http.route('/api/v1/ui/client-actions/<int:action_id>', type='http', auth='user', methods=['GET'])
    def client_action(self, action_id):
        try:
            if action_id not in _visible_action_ids('ir.actions.client'):
                raise AccessError('Action is not available for this user.')
            action = request.env['ir.actions.client'].sudo().browse(action_id).exists()
            if not action:
                raise MissingError('Action not found.')
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
            record = model.browse(action.get('res_id')).exists() if action.get('res_id') else model.browse()
            field_names = [field['name'] for field in schema['fields']]
            values = record.read(field_names)[0] if record else model.default_get(field_names)
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
            values = {name: value[0] if isinstance(value, (list, tuple)) and model._fields[name].type == 'many2one' and value else value for name, value in payload.get('values', {}).items() if name in allowed_fields}
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
    def records(self, action_id, page=1, q='', order=None, filters=None, **kw):
        try:
            action = _visible_action(action_id)
            schema = _view_schema(action)
            context, domain = _eval_action(action)
            model = request.env[action.res_model].with_context(**context)
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
                values = _serialize_form_values(model, model.default_get(fields_to_read), schema)
                return request.make_json_response({'id': None, 'values': values}, headers=[('Cache-Control', 'no-store')])
            record = model.browse(int(record_id)).exists()
            if not record:
                raise MissingError('Record not found.')
            record.check_access_rule('read')
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

    @http.route('/api/v1/ui/actions/<int:action_id>/records/<int:record_id>/button', type='http', auth='user', methods=['POST'])
    def form_button(self, action_id, record_id):
        try:
            action = _visible_action(action_id)
            schema = _view_schema(action)
            payload = _json_body()
            button_name = payload.get('name')
            button_type = payload.get('type')
            allowed = {(item['name'], item['type']) for item in schema['form']['buttons']}
            if (button_name, button_type) not in allowed:
                raise AccessError('Button is not available.')
            record = request.env[action.res_model].browse(record_id).exists()
            if not record:
                raise MissingError('Record not found.')
            record.check_access_rule('read')
            if button_type == 'object':
                result = getattr(record, button_name)()
            else:
                target = request.env['ir.actions.actions'].browse(int(button_name)).exists()
                if not target:
                    raise MissingError('Action not found.')
                action_type = target.type
                result = request.env[action_type].browse(target.id).read()[0]
            return request.make_json_response({'result': _action_payload(result)})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (AttributeError, UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/ui/actions/<int:action_id>/records', type='http', auth='user', methods=['POST'])
    def create(self, action_id):
        try:
            action = _visible_action(action_id)
            schema = _view_schema(action)
            context, _domain = _eval_action(action)
            values = _json_body().get('values', {})
            allowed = set(_allowed_fields(schema, 'form'))
            if not isinstance(values, dict) or set(values) - allowed:
                raise ValidationError('Payload contains unsupported fields.')
            values = {name: value[0] if isinstance(value, (list, tuple)) and _form_fields(schema).get(name, {}).get('type') == 'many2one' and value else value for name, value in values.items()}
            values = _normalize_form_values(values, schema)
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
            schema = _view_schema(action)
            context, _domain = _eval_action(action)
            values = _json_body().get('values', {})
            allowed = set(_allowed_fields(schema, 'form'))
            if not isinstance(values, dict) or set(values) - allowed:
                raise ValidationError('Payload contains unsupported fields.')
            record = request.env[action.res_model].with_context(**context).browse(record_id).exists()
            if not record:
                raise MissingError('Record not found.')
            values = {name: value[0] if isinstance(value, (list, tuple)) and _form_fields(schema).get(name, {}).get('type') == 'many2one' and value else value for name, value in values.items()}
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
            ids = _json_body().get('ids', [])
            if not isinstance(ids, list) or not ids or not all(isinstance(item, int) for item in ids):
                raise ValidationError('Select records to delete.')
            context, domain = _eval_action(action)
            model = request.env[action.res_model].with_context(**context)
            records = model.browse(ids).exists()
            if set(records.ids) != set(ids) or model.search_count(expression.AND([domain, [('id', 'in', ids)]])) != len(ids):
                raise AccessError('One or more records are unavailable.')
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
    def relation(self, action_id, field_name, q='', parent=None, **kw):
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
            records = relation_model.name_search(q, limit=20)
            return request.make_json_response({'items': [{'id': item_id, 'label': label} for item_id, label in records]})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

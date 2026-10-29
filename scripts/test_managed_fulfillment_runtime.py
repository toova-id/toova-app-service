#!/usr/bin/env python3
"""Run inside `odoo-bin shell`; transaction always rolls back."""

warehouse = env['stock.warehouse'].search([('company_id', '=', env.company.id)], limit=1)
assert warehouse, 'warehouse fixture required'

with env.cr.savepoint() as savepoint:
    customer = env['res.partner'].create({'name': 'Managed Fulfillment Self Check'})
    env['managed.partner.role'].create({
        'partner_id': customer.id, 'company_id': env.company.id, 'role': 'customer',
    })
    product = env['product.product'].create({
        'name': 'Managed Fulfillment Product', 'detailed_type': 'product',
        'invoice_policy': 'delivery', 'list_price': 125000,
    })
    env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 10)
    order = env['sale.order'].with_context(managed_ui=True).create({
        'partner_id': customer.id,
        'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 2})],
    })
    order.action_confirm()
    picking = order.picking_ids.filtered(lambda item: item.picking_type_code == 'outgoing')
    assert len(picking) == 1
    picking.action_assign()
    assert picking.move_line_ids_without_package
    picking.move_line_ids_without_package.qty_done = picking.move_line_ids_without_package.reserved_uom_qty
    result = picking.with_context(managed_ui=True).button_validate()
    if isinstance(result, dict) and result.get('res_model') in ('stock.immediate.transfer', 'stock.backorder.confirmation'):
        wizard = env[result['res_model']].with_context(**result.get('context', {})).create({})
        result = wizard.process()
    assert picking.state == 'done'
    assert order.invoice_status == 'to invoice'
    invoice_wizard = env['sale.advance.payment.inv'].with_context(
        active_model='sale.order', active_ids=order.ids,
    ).create({'advance_payment_method': 'delivered'})
    invoice = invoice_wizard._create_invoices(order)
    assert invoice.state == 'draft'
    invoice.action_post()
    journal = env['account.journal'].search([
        ('type', 'in', ('bank', 'cash')), ('company_id', '=', env.company.id),
    ], limit=1)
    assert journal
    payment_wizard = env['account.payment.register'].with_context(
        active_model='account.move', active_ids=invoice.ids,
    ).create({'journal_id': journal.id, 'amount': invoice.amount_residual})
    payment_wizard.action_create_payments()
    assert invoice.payment_state == 'paid'
    assert not invoice.amount_residual
    savepoint.rollback()

print('managed fulfillment runtime self-check passed')

from odoo import models, api, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id', 'product_uom_qty')
    def _onchange_verificar_stock_kit(self):
        stock_service = self.env['control.stock.service']
        for linea in self:
            if not linea.product_id or not linea.product_uom_qty:
                continue

            stock_result = stock_service.check_products_stock([{
                'product': linea.product_id,
                'quantity': linea.product_uom_qty,
            }])

            if not stock_result['stock_ok']:
                mensaje = _(
                    "No hay stock suficiente para este arreglo:\n\n%s"
                ) % stock_service.format_missing_items_message(stock_result['missing_items'])

                return {
                    'warning': {
                        'title': _('Stock insuficiente'),
                        'message': mensaje,
                    }
                }

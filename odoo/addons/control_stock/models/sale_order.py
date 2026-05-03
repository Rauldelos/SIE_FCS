from odoo import models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        stock_service = self.env['control.stock.service']
        for pedido in self:
            stock_result = stock_service.check_products_stock([
                {
                    'product': linea_pedido.product_id,
                    'quantity': linea_pedido.product_uom_qty,
                }
                for linea_pedido in pedido.order_line
                if linea_pedido.product_id and linea_pedido.product_uom_qty
            ])

            if not stock_result['stock_ok']:
                mensaje = _(
                    "No se puede confirmar el pedido porque no hay stock suficiente "
                    "de los siguientes materiales:\n\n%s"
                ) % stock_service.format_missing_items_message(stock_result['missing_items'])

                raise ValidationError(mensaje)

        return super().action_confirm()

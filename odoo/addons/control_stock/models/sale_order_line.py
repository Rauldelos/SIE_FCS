from odoo import models, api, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id', 'product_uom_qty')
    def _onchange_verificar_stock_kit(self):
        for linea in self:
            if not linea.product_id or not linea.product_uom_qty:
                continue

            producto = linea.product_id
            cantidad_pedida = linea.product_uom_qty

            lista_materiales = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', producto.product_tmpl_id.id),
                ('type', '=', 'phantom')
            ], limit=1)

            if not lista_materiales:
                continue

            errores = []

            for componente in lista_materiales.bom_line_ids:
                material = componente.product_id
                cantidad_necesaria = componente.product_qty * cantidad_pedida
                stock_disponible = material.free_qty

                if stock_disponible < cantidad_necesaria:
                    faltan = cantidad_necesaria - stock_disponible
                    errores.append(
                        _(
                            "Material: %(material)s | Necesario: %(necesario).2f | "
                            "Disponible: %(disponible).2f | Faltan: %(faltan).2f"
                        ) % {
                            'material': material.display_name,
                            'necesario': cantidad_necesaria,
                            'disponible': stock_disponible,
                            'faltan': faltan,
                        }
                    )

            if errores:
                mensaje = _(
                    "No hay stock suficiente para este arreglo:\n\n%s"
                ) % "\n".join(errores)

                return {
                    'warning': {
                        'title': _('Stock insuficiente'),
                        'message': mensaje,
                    }
                }
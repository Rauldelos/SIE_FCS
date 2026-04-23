from collections import defaultdict

from odoo import models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for pedido in self:
            materiales_requeridos = defaultdict(float)

            for linea_pedido in pedido.order_line:
                if not linea_pedido.product_id or not linea_pedido.product_uom_qty:
                    continue

                producto = linea_pedido.product_id
                cantidad_pedida = linea_pedido.product_uom_qty

                lista_materiales = self.env['mrp.bom'].search([
                    ('product_tmpl_id', '=', producto.product_tmpl_id.id),
                    ('type', '=', 'phantom')
                ], limit=1)

                if not lista_materiales:
                    continue

                for componente in lista_materiales.bom_line_ids:
                    material = componente.product_id
                    cantidad_necesaria = componente.product_qty * cantidad_pedida
                    materiales_requeridos[material] += cantidad_necesaria

            errores = []

            for material, cantidad_necesaria in materiales_requeridos.items():
                stock_disponible = material.free_qty

                if stock_disponible < cantidad_necesaria:
                    faltan = cantidad_necesaria - stock_disponible

                    errores.append(
                        _(
                            "Material: %(material)s\n"
                            "Necesario: %(necesario).2f\n"
                            "Disponible: %(disponible).2f\n"
                            "Faltan: %(faltan).2f"
                        ) % {
                            'material': material.display_name,
                            'necesario': cantidad_necesaria,
                            'disponible': stock_disponible,
                            'faltan': faltan,
                        }
                    )

            if errores:
                mensaje = _(
                    "No se puede confirmar el pedido porque no hay stock suficiente "
                    "de los siguientes materiales:\n\n%s"
                ) % ("\n\n".join(errores))

                raise ValidationError(mensaje)

        return super().action_confirm()
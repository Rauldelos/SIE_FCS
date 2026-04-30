from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FcsDeliveryOrderLine(models.Model):
    _name = 'fcs.delivery.order.line'
    _description = 'Línea de arreglo floral del pedido'
    _order = 'order_id, id'

    order_id = fields.Many2one(
        'fcs.delivery.order',
        required=True,
        ondelete='cascade',
        string='Pedido',
    )
    flower_type = fields.Selection(
        [
            ('corona', 'Corona'),
            ('centro', 'Centro'),
            ('ramo', 'Ramo'),
            ('palma', 'Palma'),
            ('otro', 'Otro'),
        ],
        required=True,
        string='Tipo de arreglo floral',
    )
    quantity = fields.Integer(required=True, default=1, string='Cantidad')
    notes = fields.Text(string='Notas')

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('La cantidad debe ser mayor que cero.'))

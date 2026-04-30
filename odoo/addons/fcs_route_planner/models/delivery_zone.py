from odoo import fields, models


class FcsDeliveryZone(models.Model):
    _name = 'fcs.delivery.zone'
    _description = 'FCS Delivery Zone'
    _order = 'distance_km, name'

    name = fields.Char(required=True)
    distance_km = fields.Float(
        required=True,
        string='Distancia aproximada (km)',
        help='Distancia aproximada desde Calle Mariano Benlliure, 85, 41005 Sevilla.',
    )
    active = fields.Boolean(default=True)
    notes = fields.Text()

from odoo import fields, models


class FcsDeliveryVehicle(models.Model):
    _name = 'fcs.delivery.vehicle'
    _description = 'FCS Delivery Vehicle'
    _order = 'name'

    name = fields.Char(required=True)
    license_plate = fields.Char(string='Matrícula')
    driver_name = fields.Char(string='Conductor')
    capacity = fields.Integer(default=5, string='Capacidad de arreglos')
    available = fields.Boolean(default=True, string='Disponible')
    active = fields.Boolean(default=True)

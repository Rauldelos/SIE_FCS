from odoo import fields, models


class FcsFuneralHome(models.Model):
    _name = 'fcs.funeral.home'
    _description = 'Tanatorio'
    _order = 'name'

    name = fields.Char(required=True)
    zone_id = fields.Many2one('fcs.delivery.zone', required=True, string='Zona/Pueblo')
    address = fields.Char(string='Dirección')
    active = fields.Boolean(default=True)
    notes = fields.Text()

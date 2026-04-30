from odoo import api, fields, models

from .constants import FCS_BASE_ADDRESS


class FcsDeliveryRoute(models.Model):
    _name = 'fcs.delivery.route'
    _description = 'FCS Delivery Route'
    _order = 'planning_date desc, id desc'

    name = fields.Char(required=True)
    planning_date = fields.Datetime(default=fields.Datetime.now, string='Fecha de planificación')
    base_address = fields.Char(default=FCS_BASE_ADDRESS, string='Dirección base')
    vehicle_id = fields.Many2one('fcs.delivery.vehicle', required=True, string='Vehículo')
    line_ids = fields.One2many('fcs.delivery.route.line', 'route_id', string='Líneas')
    average_speed_kmh = fields.Float(default=35.0, string='Velocidad media (km/h)')
    total_km = fields.Float(
        compute='_compute_total_km',
        readonly=True,
        store=True,
        string='Km totales',
    )
    estimated_return_time_minutes = fields.Integer(
        compute='_compute_estimated_return_time',
        readonly=True,
        store=True,
        string='Tiempo estimado de regreso (min)',
    )
    estimated_return_time_text = fields.Char(
        compute='_compute_estimated_return_time',
        readonly=True,
        store=True,
        string='Tiempo estimado de regreso',
    )
    route_notes = fields.Text(string='Notas de ruta')
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmada'),
            ('done', 'Realizada'),
        ],
        default='draft',
        string='Estado',
    )

    @api.depends('line_ids.estimated_km')
    def _compute_total_km(self):
        for route in self:
            # Approximation based on configured zone distances. A future version can
            # use Google Maps Distance Matrix from FCS_BASE_ADDRESS for real routes.
            route.total_km = sum(route.line_ids.mapped('estimated_km'))

    @api.depends('line_ids.estimated_km', 'line_ids.sequence', 'average_speed_kmh')
    def _compute_estimated_return_time(self):
        for route in self:
            sorted_lines = route.line_ids.sorted(lambda line: (line.sequence, line.id))
            return_distance = sorted_lines[-1].estimated_km if sorted_lines else 0.0
            speed = route.average_speed_kmh or 35.0
            # Temporary approximation with the last delivery zone distance. Later this
            # should be replaced by Google Maps API to calculate the real return from
            # the last destination to Calle Mariano Benlliure, 85, 41005 Sevilla.
            minutes = int(round((return_distance / speed) * 60.0)) if return_distance else 0
            route.estimated_return_time_minutes = minutes
            route.estimated_return_time_text = f'{minutes} min'

    def action_confirm_route(self):
        self.write({'state': 'confirmed'})
        return True

    def action_done_route(self):
        for route in self:
            route.line_ids.mapped('order_id').write({'state': 'delivered'})
        self.write({'state': 'done'})
        return True


class FcsDeliveryRouteLine(models.Model):
    _name = 'fcs.delivery.route.line'
    _description = 'FCS Delivery Route Line'
    _order = 'sequence, id'

    route_id = fields.Many2one(
        'fcs.delivery.route',
        required=True,
        ondelete='cascade',
        string='Ruta',
    )
    order_id = fields.Many2one('fcs.delivery.order', required=True, string='Pedido')
    sequence = fields.Integer(string='Secuencia')
    zone_id = fields.Many2one(
        'fcs.delivery.zone',
        related='order_id.zone_id',
        readonly=True,
        store=True,
        string='Zona/Pueblo',
    )
    delivery_address = fields.Char(
        related='order_id.delivery_address',
        readonly=True,
        store=True,
        string='Dirección de entrega',
    )
    order_time = fields.Datetime(
        related='order_id.order_time',
        readonly=True,
        store=True,
        string='Hora de entrada',
    )
    estimated_km = fields.Float(
        related='order_id.estimated_km',
        readonly=True,
        store=True,
        string='Km estimados',
    )
    estimated_arrival_datetime = fields.Datetime(string='Llegada estimada')
    estimated_arrival_minutes = fields.Float(string='Minutos hasta llegada')
    delay_minutes = fields.Float(string='Retraso (min)')

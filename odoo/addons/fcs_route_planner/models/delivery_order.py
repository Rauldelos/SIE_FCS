from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FcsDeliveryOrder(models.Model):
    _name = 'fcs.delivery.order'
    _description = 'FCS Delivery Order'
    _order = 'order_time, id'

    name = fields.Char(required=True, string='Referencia')
    customer_name = fields.Char(required=True, string='Cliente')
    zone_id = fields.Many2one('fcs.delivery.zone', required=True, string='Zona/Pueblo')
    delivery_type = fields.Selection(
        [
            ('funeral_home', 'Tanatorio'),
            ('home', 'Domicilio'),
        ],
        required=True,
        default='funeral_home',
        string='Tipo de entrega',
    )
    funeral_home_id = fields.Many2one('fcs.funeral.home', string='Tanatorio')
    home_address = fields.Char(string='Dirección de domicilio')
    delivery_address = fields.Char(readonly=True, string='Dirección final')
    order_time = fields.Datetime(required=True, string='Hora de entrada')
    deadline_datetime = fields.Datetime(
        compute='_compute_deadline_datetime',
        readonly=True,
        store=True,
        string='Fecha límite de entrega',
    )
    estimated_delivery_datetime = fields.Datetime(
        readonly=True,
        string='Entrega estimada',
    )
    estimated_delay_minutes = fields.Float(
        readonly=True,
        string='Retraso estimado (min)',
    )
    urgency_score = fields.Float(
        readonly=True,
        string='Urgencia',
    )
    # Deprecated: kept for database compatibility. New orders use line_ids.
    flower_type = fields.Selection(
        [
            ('corona', 'Corona'),
            ('centro', 'Centro'),
            ('ramo', 'Ramo'),
            ('palma', 'Palma'),
            ('otro', 'Otro'),
        ],
        string='Tipo de arreglo floral',
    )
    line_ids = fields.One2many(
        'fcs.delivery.order.line',
        'order_id',
        string='Arreglos florales',
    )
    total_items = fields.Integer(
        compute='_compute_total_items',
        readonly=True,
        store=True,
        string='Total de arreglos',
    )
    state = fields.Selection(
        [
            ('pending', 'Pendiente'),
            ('prepared', 'Preparado'),
            ('planned', 'Planificado'),
            ('delivered', 'Entregado'),
            ('cancelled', 'Cancelado'),
        ],
        default='pending',
        string='Estado',
    )
    vehicle_id = fields.Many2one(
        'fcs.delivery.vehicle',
        readonly=True,
        string='Vehículo asignado',
    )
    route_id = fields.Many2one(
        'fcs.delivery.route',
        readonly=True,
        string='Ruta',
    )
    route_order = fields.Integer(readonly=True, string='Orden en ruta')
    estimated_km = fields.Float(
        compute='_compute_estimated_km',
        readonly=True,
        store=True,
        string='Km estimados',
    )
    priority_score = fields.Float(
        compute='_compute_priority_score',
        readonly=True,
        string='Prioridad',
    )
    notes = fields.Text()
    stock_consumed = fields.Boolean(
        readonly=True,
        string='Stock consumido',
    )
    stock_move_ids = fields.Many2many(
        'stock.move',
        readonly=True,
        string='Movimientos de stock',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._complete_delivery_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        for order in self:
            order_vals = vals.copy()
            order._complete_delivery_values(order_vals)
            super(FcsDeliveryOrder, order).write(order_vals)
        return True

    def _complete_delivery_values(self, vals):
        delivery_type = (
            vals['delivery_type']
            if 'delivery_type' in vals
            else (self.delivery_type if self else 'funeral_home')
        )
        funeral_home_id = (
            vals['funeral_home_id']
            if 'funeral_home_id' in vals
            else (self.funeral_home_id.id if self else False)
        )

        if delivery_type == 'funeral_home' and funeral_home_id:
            funeral_home = self.env['fcs.funeral.home'].browse(funeral_home_id)
            if funeral_home.exists():
                if not vals.get('zone_id'):
                    vals['zone_id'] = funeral_home.zone_id.id
                vals['delivery_address'] = funeral_home.address or funeral_home.name
        elif delivery_type == 'home':
            vals['delivery_address'] = (
                vals['home_address']
                if 'home_address' in vals
                else (self.home_address if self else False)
            )

    @api.onchange('delivery_type', 'funeral_home_id', 'home_address')
    def _onchange_delivery_details(self):
        for order in self:
            if order.delivery_type == 'funeral_home':
                if order.funeral_home_id:
                    order.zone_id = order.funeral_home_id.zone_id
                    order.delivery_address = (
                        order.funeral_home_id.address or order.funeral_home_id.name
                    )
                else:
                    order.delivery_address = False
            else:
                order.delivery_address = order.home_address

    @api.constrains('delivery_type', 'funeral_home_id', 'home_address')
    def _check_delivery_details(self):
        for order in self:
            if order.delivery_type == 'funeral_home' and not order.funeral_home_id:
                raise ValidationError(_('Debe seleccionar un tanatorio para este pedido.'))
            if order.delivery_type == 'home' and not order.home_address:
                raise ValidationError(_('Debe indicar la dirección del domicilio.'))

    @api.depends('line_ids.quantity')
    def _compute_total_items(self):
        for order in self:
            order.total_items = sum(order.line_ids.mapped('quantity'))

    @api.depends('order_time')
    def _compute_deadline_datetime(self):
        for order in self:
            order.deadline_datetime = order._get_deadline_datetime(3.0)

    @api.depends('zone_id.distance_km')
    def _compute_estimated_km(self):
        for order in self:
            # Future improvement: replace this approximate zone distance with
            # Google Maps API using Calle Mariano Benlliure, 85, 41005 Sevilla as origin.
            order.estimated_km = order.zone_id.distance_km or 0.0

    @api.depends('order_time', 'zone_id.distance_km')
    def _compute_priority_score(self):
        now = fields.Datetime.now()
        for order in self:
            order.priority_score = order._get_priority_score(now)

    def _get_priority_score(self, planning_datetime):
        self.ensure_one()
        if not self.order_time:
            return 0.0

        planning_dt = fields.Datetime.to_datetime(planning_datetime) or fields.Datetime.now()
        order_dt = fields.Datetime.to_datetime(self.order_time)
        age_hours = max((planning_dt - order_dt).total_seconds() / 3600.0, 0.0)
        distance_km = self.zone_id.distance_km or 0.0
        return (age_hours * 10.0) - distance_km

    def _get_deadline_datetime(self, max_delivery_hours=3.0):
        self.ensure_one()
        if not self.order_time:
            return False
        order_dt = fields.Datetime.to_datetime(self.order_time)
        return order_dt + timedelta(hours=max_delivery_hours or 3.0)

    def _get_urgency_score(self, planning_datetime, max_delivery_hours=3.0):
        self.ensure_one()
        if not self.order_time:
            return 0.0

        planning_dt = fields.Datetime.to_datetime(planning_datetime) or fields.Datetime.now()
        order_dt = fields.Datetime.to_datetime(self.order_time)
        elapsed_hours = max((planning_dt - order_dt).total_seconds() / 3600.0, 0.0)
        delivery_hours = max(max_delivery_hours or 3.0, 0.01)
        urgency_ratio = min(max(elapsed_hours / delivery_hours, 0.0), 1.5)
        return urgency_ratio * 100.0

    def check_fcs_order_stock(self):
        self.ensure_one()
        return self.env['fcs.stock.integration.service'].check_fcs_order_stock(self)

    def action_confirm_preparation_from_bonita(self):
        self.ensure_one()
        stock_result = self.check_fcs_order_stock()
        if not stock_result['stock_ok'] and not self.stock_consumed:
            return {
                'success': False,
                'stock_ok': False,
                'missing_items': stock_result['missing_items'],
                'state': self.state,
            }

        consume_result = self.env['fcs.stock.integration.service'].consume_fcs_order_stock(self)
        if not consume_result.get('success'):
            return {
                'success': False,
                'stock_ok': False,
                'missing_items': consume_result.get('missing_items', []),
                'state': self.state,
            }

        self.write({'state': 'prepared'})
        return {
            'success': True,
            'stock_ok': True,
            'missing_items': [],
            'state': self.state,
            'stock_consumed': self.stock_consumed,
            'stock_move_ids': self.stock_move_ids.ids,
        }

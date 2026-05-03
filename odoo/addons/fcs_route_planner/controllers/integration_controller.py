import json
import unicodedata
from datetime import datetime, timezone

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class FcsRouteIntegrationController(http.Controller):
    API_TOKEN = 'fcs-demo-token'

    @http.route('/fcs_route/create_order', type='http', auth='public', methods=['POST'], csrf=False)
    def create_order(self, **kwargs):
        return self._handle(self._create_order)

    @http.route('/fcs_route/check_stock', type='http', auth='public', methods=['POST'], csrf=False)
    def check_stock(self, **kwargs):
        return self._handle(self._check_stock)

    @http.route('/fcs_route/confirm_preparation', type='http', auth='public', methods=['POST'], csrf=False)
    def confirm_preparation(self, **kwargs):
        return self._handle(self._confirm_preparation)

    @http.route('/fcs_route/plan_routes', type='http', auth='public', methods=['POST'], csrf=False)
    def plan_routes(self, **kwargs):
        return self._handle(self._plan_routes)

    @http.route('/fcs_route/route_queue', type='http', auth='public', methods=['POST'], csrf=False)
    def route_queue(self, **kwargs):
        return self._handle(self._route_queue)

    @http.route('/fcs_route/order_status', type='http', auth='public', methods=['POST'], csrf=False)
    def order_status(self, **kwargs):
        return self._handle(self._order_status)

    @http.route('/fcs_route/mark_delivered', type='http', auth='public', methods=['POST'], csrf=False)
    def mark_delivered(self, **kwargs):
        return self._handle(self._mark_delivered)

    def _handle(self, handler):
        try:
            payload = self._get_payload()
            self._check_token(payload)
            return self._json_response(handler(payload))
        except (UserError, ValidationError, ValueError) as error:
            return self._json_response({
                'success': False,
                'error': str(error),
            })
        except Exception as error:
            return self._json_response({
                'success': False,
                'error': 'Error interno en la integracion FCS: %s' % error,
            })

    def _create_order(self, payload):
        env = request.env
        delivery_type = payload.get('delivery_type') or 'funeral_home'
        zone = self._resolve_zone(payload)
        funeral_home = self._resolve_funeral_home(payload) if delivery_type == 'funeral_home' else False

        if delivery_type == 'funeral_home' and not funeral_home:
            raise UserError('Debe indicar funeral_home_id o funeral_home_name.')
        if delivery_type == 'home' and not payload.get('home_address'):
            raise UserError('Debe indicar home_address para entregas a domicilio.')
        if not zone and funeral_home:
            zone = funeral_home.zone_id
        if not zone:
            raise UserError('Debe indicar zone_id o zone_name valido.')

        fcs_stock = env['fcs.stock.integration.service'].sudo()
        order_lines = [
            (0, 0, fcs_stock.prepare_order_line_values(line))
            for line in payload.get('lines', [])
        ]
        if not order_lines:
            raise UserError('Debe enviar al menos una linea de pedido.')

        order = env['fcs.delivery.order'].sudo().create({
            'name': payload.get('name') or self._next_order_name(),
            'customer_name': payload.get('customer_name') or 'Cliente Bonita',
            'delivery_type': delivery_type,
            'zone_id': zone.id,
            'funeral_home_id': funeral_home.id if funeral_home else False,
            'home_address': payload.get('home_address'),
            'order_time': self._parse_datetime(payload.get('order_time')),
            'line_ids': order_lines,
            'notes': payload.get('notes'),
        })
        stock_result = order.check_fcs_order_stock()

        return {
            'success': True,
            'order_id': order.id,
            'order_name': order.name,
            'state': order.state,
            'stock_ok': stock_result['stock_ok'],
            'missing_items': stock_result['missing_items'],
        }

    def _check_stock(self, payload):
        service = request.env['fcs.stock.integration.service'].sudo()
        service.ensure_stock_payload_has_lines(payload)

        if payload.get('order_id'):
            order = self._get_order(payload['order_id'])
            result = order.check_fcs_order_stock()
        else:
            result = service.check_fcs_lines_stock(payload.get('lines', []))

        return {
            'success': True,
            'stock_ok': result['stock_ok'],
            'missing_items': result['missing_items'],
        }

    def _confirm_preparation(self, payload):
        order = self._get_order(payload.get('order_id'))
        result = order.action_confirm_preparation_from_bonita()
        return result

    def _plan_routes(self, payload):
        if payload.get('batch') is not True:
            raise UserError(
                'La planificacion de rutas debe ejecutarse explicitamente por lote '
                'enviando batch=true.'
            )

        before_routes = request.env['fcs.delivery.route'].sudo().search([])
        ready_orders = self._get_route_queue_orders()
        if not ready_orders:
            raise UserError('No hay pedidos preparados pendientes de ruta.')

        minimum_orders = int(payload.get('minimum_orders') or 0)
        if minimum_orders and len(ready_orders) < minimum_orders:
            return {
                'success': True,
                'planning_executed': False,
                'orders_ready_count': len(ready_orders),
                'minimum_orders': minimum_orders,
                'message': 'Aun no hay suficientes pedidos preparados para planificar por lote.',
            }

        wizard = request.env['fcs.route.planning.wizard'].sudo().create({
            'planning_datetime': fields.Datetime.now(),
            'include_pending_only': True,
            'max_delivery_hours': 3.0,
            'allow_reasonable_detours': True,
            'max_reasonable_detour_minutes': 25,
            'notes': payload.get('notes') or 'Planificacion solicitada desde Bonita',
        })
        wizard.action_plan_routes()
        after_routes = request.env['fcs.delivery.route'].sudo().search([])
        created_routes = after_routes - before_routes
        planned_orders = created_routes.mapped('line_ids.order_id')

        return {
            'success': True,
            'planning_executed': True,
            'routes_created': created_routes.ids,
            'orders_planned': planned_orders.ids,
            'orders_waiting_before_planning': ready_orders.ids,
            'message': 'Rutas planificadas por lote correctamente',
        }

    def _route_queue(self, payload):
        orders = self._get_route_queue_orders()
        return {
            'success': True,
            'orders_ready': [
                {
                    'order_id': order.id,
                    'order_name': order.name,
                    'customer_name': order.customer_name,
                    'total_items': order.total_items,
                    'zone': order.zone_id.name,
                    'deadline_datetime': self._format_datetime(order.deadline_datetime),
                    'estimated_km': order.estimated_km,
                }
                for order in orders
            ],
            'count': len(orders),
        }

    def _order_status(self, payload):
        order = self._get_order(payload.get('order_id'))
        stock_result = (
            {'stock_ok': True, 'missing_items': []}
            if order.stock_consumed
            else order.check_fcs_order_stock()
        )

        return {
            'success': True,
            'order_id': order.id,
            'state': order.state,
            'stock_ok': stock_result['stock_ok'],
            'missing_items': stock_result['missing_items'],
            'vehicle': order.vehicle_id.name or False,
            'route': order.route_id.name or False,
            'route_order': order.route_order,
            'estimated_delivery_datetime': self._format_datetime(order.estimated_delivery_datetime),
            'estimated_delay_minutes': order.estimated_delay_minutes,
            'stock_consumed': order.stock_consumed,
        }

    def _mark_delivered(self, payload):
        order = self._get_order(payload.get('order_id'))
        order.sudo().write({'state': 'delivered'})
        return {
            'success': True,
            'order_id': order.id,
            'state': order.state,
        }

    def _get_payload(self):
        raw_body = request.httprequest.get_data(as_text=True)
        if not raw_body:
            return {}
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            raise ValueError('El cuerpo de la peticion debe ser JSON valido.')

    def _check_token(self, payload):
        if payload.get('api_token') != self.API_TOKEN:
            raise UserError('api_token no valido.')

    def _json_response(self, payload):
        return request.make_response(
            json.dumps(payload, default=str),
            headers=[('Content-Type', 'application/json')],
        )

    def _get_order(self, order_id):
        if not order_id:
            raise UserError('Debe indicar order_id.')
        order = request.env['fcs.delivery.order'].sudo().browse(int(order_id))
        if not order.exists():
            raise UserError('No existe el pedido FCS con id %s.' % order_id)
        return order

    def _get_route_queue_orders(self):
        return request.env['fcs.delivery.order'].sudo().search([
            ('state', '=', 'prepared'),
            ('route_id', '=', False),
        ])

    def _resolve_zone(self, payload):
        zone_model = request.env['fcs.delivery.zone'].sudo()
        if payload.get('zone_id'):
            zone = zone_model.browse(int(payload['zone_id']))
            return zone if zone.exists() else zone_model
        if payload.get('zone_name'):
            return self._search_by_name(zone_model, payload['zone_name'])
        return zone_model

    def _resolve_funeral_home(self, payload):
        funeral_home_model = request.env['fcs.funeral.home'].sudo()
        if payload.get('funeral_home_id'):
            funeral_home = funeral_home_model.browse(int(payload['funeral_home_id']))
            return funeral_home if funeral_home.exists() else funeral_home_model
        if payload.get('funeral_home_name'):
            return self._search_by_name(funeral_home_model, payload['funeral_home_name'])
        return funeral_home_model

    def _search_by_name(self, model, name):
        record = model.search([('name', 'ilike', name)], limit=1)
        if record:
            return record

        normalized_name = self._normalize_text(name)
        for candidate in model.search([]):
            if normalized_name in self._normalize_text(candidate.name):
                return candidate
        return model

    def _normalize_text(self, value):
        value = value or ''
        normalized = unicodedata.normalize('NFKD', value)
        return ''.join(
            char for char in normalized
            if not unicodedata.combining(char)
        ).lower()

    def _parse_datetime(self, value):
        if not value:
            return fields.Datetime.now()
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if parsed.tzinfo:
                    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
                return fields.Datetime.to_string(parsed)
            except ValueError:
                return fields.Datetime.to_string(fields.Datetime.to_datetime(value))
        return value

    def _format_datetime(self, value):
        if not value:
            return False
        return fields.Datetime.to_string(value)

    def _next_order_name(self):
        return 'BONITA-%s' % fields.Datetime.now().strftime('%Y%m%d%H%M%S')

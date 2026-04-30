from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.fcs_route_planner.models.constants import FCS_BASE_ADDRESS


class FcsRoutePlanningWizard(models.TransientModel):
    _name = 'fcs.route.planning.wizard'
    _description = 'FCS Route Planning Wizard'

    INTERNAL_AVERAGE_SPEED_KMH = 35.0
    INTERNAL_MAX_REASONABLE_DETOUR_MINUTES = 25

    max_orders_per_vehicle = fields.Integer(default=5, string='Máximo de pedidos por vehículo')
    planning_datetime = fields.Datetime(default=fields.Datetime.now, string='Fecha de planificación')
    include_pending_only = fields.Boolean(default=True, string='Solo pedidos pendientes')
    max_delivery_hours = fields.Float(default=3.0, string='Horas máximas de entrega')
    average_speed_kmh = fields.Float(default=35.0, string='Velocidad media (km/h)')
    allow_reasonable_detours = fields.Boolean(default=True, string='Permitir desvíos razonables')
    max_reasonable_detour_minutes = fields.Integer(default=25, string='Desvío máximo razonable (min)')
    notes = fields.Text()
    base_address = fields.Char(default=FCS_BASE_ADDRESS, string='Dirección base')

    def action_plan_routes(self):
        self.ensure_one()
        self._validate_planning_values()

        orders = self.env['fcs.delivery.order'].search(self._get_order_domain())
        if not orders:
            raise UserError(_('No hay pedidos disponibles para planificar.'))

        vehicles = self.env['fcs.delivery.vehicle'].search([
            ('available', '=', True),
            ('active', '=', True),
        ])
        if not vehicles:
            raise UserError(_('No hay vehículos disponibles para planificar rutas.'))

        route_plans = self._build_route_plans(vehicles)
        if not route_plans:
            raise UserError(_('No hay vehículos disponibles con capacidad mayor que cero.'))

        planning_dt = fields.Datetime.to_datetime(self.planning_datetime) or fields.Datetime.now()
        metrics = self._build_order_metrics(orders, planning_dt)
        ordered_candidates = self._sort_orders_for_planning(orders, metrics)

        # Persist current urgency so users can see why a pending order was prioritized.
        for order in orders:
            order.write({'urgency_score': metrics[order.id]['urgency_score']})

        unassigned_orders = self.env['fcs.delivery.order']
        for order in ordered_candidates:
            best_candidate = self._find_best_candidate(order, route_plans, metrics, planning_dt)
            if not best_candidate:
                unassigned_orders |= order
                continue

            plan = best_candidate['plan']
            plan['orders'] = best_candidate['route_orders']
            plan['schedule'] = best_candidate['schedule']
            plan['capacity_used'] = best_candidate['capacity_used']

        routes = self._create_routes_from_plans(route_plans, metrics, planning_dt)
        if not routes:
            raise UserError(_('No se pudo crear ninguna ruta. Revise la capacidad de los vehículos.'))

        if unassigned_orders:
            routes.write({
                'route_notes': _(
                    '%(notes)s\nPedidos sin asignar por falta de capacidad: %(orders)s'
                ) % {
                    'notes': self.notes or '',
                    'orders': ', '.join(unassigned_orders.mapped('name')),
                }
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Rutas planificadas'),
            'res_model': 'fcs.delivery.route',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', routes.ids)],
        }

    def _validate_planning_values(self):
        if self.max_delivery_hours <= 0:
            raise UserError(_('Las horas máximas de entrega deben ser mayores que cero.'))

    def _get_order_domain(self):
        if self.include_pending_only:
            return [('state', '=', 'pending')]
        return [
            ('state', 'not in', ['delivered', 'cancelled']),
            ('route_id', '=', False),
        ]

    def _build_route_plans(self, vehicles):
        plans = []
        for vehicle in vehicles:
            capacity = vehicle.capacity or 0
            if capacity <= 0:
                continue
            plans.append({
                'vehicle': vehicle,
                'capacity': capacity,
                'capacity_used': 0,
                'orders': [],
                'schedule': {},
            })
        return plans

    def _build_order_metrics(self, orders, planning_dt):
        metrics = {}
        ordered_by_time = orders.sorted(lambda order: (order.order_time, order.id))
        for order_index, order in enumerate(ordered_by_time):
            deadline = order._get_deadline_datetime(self.max_delivery_hours)
            urgency_score = order._get_urgency_score(planning_dt, self.max_delivery_hours)
            urgency_ratio = min(max(urgency_score / 100.0, 0.0), 1.5)
            metrics[order.id] = {
                'deadline': deadline,
                'urgency_score': urgency_score,
                'urgency_ratio': urgency_ratio,
                'order_index': order_index,
            }
        return metrics

    def _sort_orders_for_planning(self, orders, metrics):
        return orders.sorted(
            key=lambda order: (
                order.order_time,
                -metrics[order.id]['urgency_score'],
                order.estimated_km,
                order.id,
            )
        )

    def _find_best_candidate(self, order, route_plans, metrics, planning_dt):
        candidates = []
        for plan in route_plans:
            candidate = self._evaluate_candidate(plan, order, metrics, planning_dt)
            if candidate:
                candidates.append(candidate)
        if not candidates:
            return False
        return min(candidates, key=lambda candidate: candidate['score'])

    def _evaluate_candidate(self, plan, order, metrics, planning_dt):
        order_capacity = self._get_order_capacity_units(order)
        capacity_used = plan.get('capacity_used', 0) + order_capacity
        if capacity_used > plan['capacity']:
            return False

        proposed_orders = list(plan['orders']) + [order]
        route_orders = self._sort_orders_inside_route(proposed_orders, metrics)
        schedule = self._estimate_route_schedule(route_orders, metrics, planning_dt)
        additional_km = self._estimate_additional_km(plan['orders'], order)
        detour_minutes = self._travel_minutes(additional_km)

        order_delay = schedule[order.id]['delay_minutes']
        old_schedule = plan.get('schedule') or {}
        existing_delay_delta = 0.0
        newly_late_minutes = 0.0

        for existing_order in plan['orders']:
            old_delay = old_schedule.get(existing_order.id, {}).get('delay_minutes', 0.0)
            new_delay = schedule[existing_order.id]['delay_minutes']
            if old_delay <= 0 and new_delay > 0:
                newly_late_minutes += new_delay
            if new_delay > old_delay:
                existing_delay_delta += new_delay - old_delay

        delay_penalty = (order_delay * 20.0) + (existing_delay_delta * 10.0)
        if newly_late_minutes:
            delay_penalty += 10000.0 + (newly_late_minutes * 50.0)

        urgency_score = metrics[order.id]['urgency_score']
        order_position_penalty = self._get_order_position_penalty(route_orders, metrics)
        route_load_penalty = plan.get('capacity_used', 0) * 4.0

        score = (
            delay_penalty
            + (additional_km * 5.0)
            + order_position_penalty
            + route_load_penalty
            - urgency_score
        )

        if plan['orders'] and self.allow_reasonable_detours:
            # Internal temporary threshold until Google Maps provides real detour times.
            if detour_minutes > self.INTERNAL_MAX_REASONABLE_DETOUR_MINUTES:
                score += (
                    1000.0
                    + ((detour_minutes - self.INTERNAL_MAX_REASONABLE_DETOUR_MINUTES) * 20.0)
                )
        elif plan['orders']:
            score += detour_minutes * 8.0

        # Critical orders get a real chance to occupy an empty vehicle instead of
        # being forced into a long route that risks the three-hour delivery window.
        if metrics[order.id]['urgency_ratio'] >= 0.8 and not plan['orders']:
            score -= 75.0

        return {
            'plan': plan,
            'score': score,
            'route_orders': route_orders,
            'schedule': schedule,
            'capacity_used': capacity_used,
        }

    def _sort_orders_inside_route(self, orders, metrics):
        return sorted(
            orders,
            key=lambda order: (
                metrics[order.id]['deadline'],
                order.estimated_km,
                order.order_time,
                order.id,
            )
        )

    def _estimate_route_schedule(self, route_orders, metrics, planning_dt):
        schedule = {}
        previous_order = False
        elapsed_minutes = 0.0

        for order in route_orders:
            # This uses zone distance as a lightweight stand-in for a real distance
            # matrix. Later it can be replaced by Google Maps travel times.
            leg_km = self._estimate_leg_km(previous_order, order)
            elapsed_minutes += self._travel_minutes(leg_km)
            arrival_datetime = planning_dt + timedelta(minutes=elapsed_minutes)
            deadline = metrics[order.id]['deadline']
            delay_minutes = 0.0
            if deadline and arrival_datetime > deadline:
                delay_minutes = (arrival_datetime - deadline).total_seconds() / 60.0

            schedule[order.id] = {
                'arrival_datetime': arrival_datetime,
                'arrival_minutes': elapsed_minutes,
                'delay_minutes': delay_minutes,
            }
            previous_order = order

        return schedule

    def _estimate_leg_km(self, previous_order, order):
        distance = order.estimated_km or 0.0
        if not previous_order:
            return distance

        previous_distance = previous_order.estimated_km or 0.0
        distance_gap = abs(distance - previous_distance)
        clustered_leg = distance_gap + (distance * 0.25)
        if distance:
            clustered_leg = max(clustered_leg, min(distance, 1.0))
        return min(distance, clustered_leg)

    def _estimate_additional_km(self, route_orders, order):
        distance = order.estimated_km or 0.0
        if not route_orders:
            return distance

        route_distances = [route_order.estimated_km or 0.0 for route_order in route_orders]
        nearest_gap = min(abs(distance - route_distance) for route_distance in route_distances)
        current_span = max(route_distances) - min(route_distances)
        new_distances = route_distances + [distance]
        new_span = max(new_distances) - min(new_distances)
        span_increase = max(new_span - current_span, 0.0)

        # Nearby zones should be cheap to group; far jumps stay expensive until a
        # real Google Maps distance matrix replaces distance_km.
        clustered_extra = nearest_gap + (distance * 0.25) + (span_increase * 0.5)
        if distance:
            clustered_extra = max(clustered_extra, min(distance, 1.0))
        return min(distance, clustered_extra)

    def _travel_minutes(self, distance_km):
        # Temporary average speed until Google Maps replaces this approximation.
        return ((distance_km or 0.0) / self.INTERNAL_AVERAGE_SPEED_KMH) * 60.0

    def _get_order_capacity_units(self, order):
        return max(order.total_items or 0, 1)

    def _get_order_position_penalty(self, route_orders, metrics):
        penalty = 0.0
        expected_positions = {
            order.id: index
            for index, order in enumerate(
                sorted(route_orders, key=lambda order: metrics[order.id]['order_index'])
            )
        }

        for actual_position, order in enumerate(route_orders):
            penalty += abs(actual_position - expected_positions[order.id]) * 5.0

        return penalty

    def _create_routes_from_plans(self, route_plans, metrics, planning_dt):
        routes = self.env['fcs.delivery.route']
        route_line_model = self.env['fcs.delivery.route.line']

        for plan in route_plans:
            if not plan['orders']:
                continue

            schedule = self._estimate_route_schedule(plan['orders'], metrics, planning_dt)
            route = self.env['fcs.delivery.route'].create({
                'name': _('Ruta %(vehicle)s - %(date)s') % {
                    'vehicle': plan['vehicle'].name,
                    'date': fields.Datetime.to_string(planning_dt),
                },
                'planning_date': planning_dt,
                'base_address': self.base_address or FCS_BASE_ADDRESS,
                'vehicle_id': plan['vehicle'].id,
                'average_speed_kmh': self.INTERNAL_AVERAGE_SPEED_KMH,
                'route_notes': self.notes,
            })

            line_values = []
            for sequence, order in enumerate(plan['orders'], start=1):
                order_schedule = schedule[order.id]
                line_values.append({
                    'route_id': route.id,
                    'order_id': order.id,
                    'sequence': sequence,
                    'estimated_arrival_datetime': order_schedule['arrival_datetime'],
                    'estimated_arrival_minutes': order_schedule['arrival_minutes'],
                    'delay_minutes': order_schedule['delay_minutes'],
                })
                order.write({
                    'state': 'planned',
                    'vehicle_id': plan['vehicle'].id,
                    'route_id': route.id,
                    'route_order': sequence,
                    'urgency_score': metrics[order.id]['urgency_score'],
                    'estimated_delivery_datetime': order_schedule['arrival_datetime'],
                    'estimated_delay_minutes': order_schedule['delay_minutes'],
                })

            route_line_model.create(line_values)
            routes |= route

        return routes

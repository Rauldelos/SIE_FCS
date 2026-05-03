from odoo import _, models
from odoo.exceptions import UserError


class FcsStockIntegrationService(models.AbstractModel):
    _name = 'fcs.stock.integration.service'
    _description = 'FCS adapter for stock checks and consumption'

    FLOWER_TYPE_TERMS = {
        'corona': ['corona'],
        'centro': ['centro'],
        'ramo': ['ramo'],
        'palma': ['palma'],
        'otro': [],
    }

    def prepare_order_line_values(self, line):
        product = self._resolve_product_from_payload(line)
        flower_type = line.get('flower_type') or self._guess_flower_type(product) or 'otro'
        quantity = int(line.get('quantity') or 1)
        values = {
            'flower_type': flower_type,
            'quantity': quantity,
            'notes': line.get('notes'),
        }
        if product:
            values['product_id'] = product.id
        return values

    def check_fcs_order_stock(self, order):
        order.ensure_one()
        lines = []
        unresolved_items = []

        for order_line in order.line_ids:
            product = order_line.product_id or self._resolve_product_from_flower_type(
                order_line.flower_type
            )
            if not product:
                unresolved_items.append(self._format_unresolved_line(order_line))
                continue

            lines.append({
                'product': product,
                'quantity': order_line.quantity,
            })

        return self._check_lines(lines, unresolved_items)

    def check_fcs_lines_stock(self, payload_lines):
        lines = []
        unresolved_items = []

        for payload_line in payload_lines or []:
            product = self._resolve_product_from_payload(payload_line)
            if not product:
                unresolved_items.append(self._format_unresolved_payload(payload_line))
                continue
            lines.append({
                'product': product,
                'quantity': payload_line.get('quantity') or 1,
            })

        return self._check_lines(lines, unresolved_items)

    def consume_fcs_order_stock(self, order):
        order.ensure_one()
        if order.stock_consumed:
            return {
                'success': True,
                'stock_ok': True,
                'missing_items': [],
                'stock_move_ids': order.stock_move_ids.ids,
                'already_consumed': True,
            }

        lines = []
        unresolved_items = []
        for order_line in order.line_ids:
            product = order_line.product_id or self._resolve_product_from_flower_type(
                order_line.flower_type
            )
            if not product:
                unresolved_items.append(self._format_unresolved_line(order_line))
                continue
            lines.append({
                'product': product,
                'quantity': order_line.quantity,
            })

        if unresolved_items:
            return {
                'success': False,
                'stock_ok': False,
                'missing_items': unresolved_items,
                'stock_move_ids': [],
            }

        result = self.env['control.stock.service'].consume_products_stock(
            lines,
            reference=order.name,
        )
        if result.get('success'):
            order.write({
                'stock_consumed': True,
                'stock_move_ids': [(6, 0, result.get('stock_move_ids', []))],
            })
        return result

    def _check_lines(self, lines, unresolved_items):
        stock_result = self.env['control.stock.service'].check_products_stock(lines)
        missing_items = unresolved_items + stock_result['missing_items']
        return {
            'stock_ok': not missing_items,
            'missing_items': missing_items,
        }

    def _resolve_product_from_payload(self, line):
        product_id = line.get('product_id')
        if product_id:
            product = self.env['product.product'].sudo().browse(int(product_id))
            if product.exists():
                return product

        product_name = line.get('product_name')
        if product_name:
            product = self.env['product.product'].sudo().search([
                ('name', 'ilike', product_name),
            ], limit=1)
            if product:
                return product

        flower_type = line.get('flower_type')
        if flower_type:
            return self._resolve_product_from_flower_type(flower_type)

        return self.env['product.product']

    def _resolve_product_from_flower_type(self, flower_type):
        for term in self.FLOWER_TYPE_TERMS.get(flower_type, []):
            product = self.env['product.product'].sudo().search([
                ('name', 'ilike', term),
            ], limit=1)
            if product:
                return product
        return self.env['product.product']

    def _guess_flower_type(self, product):
        if not product:
            return False

        display_name = product.display_name.lower()
        for flower_type, terms in self.FLOWER_TYPE_TERMS.items():
            if any(term in display_name for term in terms):
                return flower_type
        return 'otro'

    def _format_unresolved_line(self, order_line):
        label = dict(order_line._fields['flower_type'].selection).get(
            order_line.flower_type,
            order_line.flower_type,
        )
        return self._format_unresolved_item(label, order_line.quantity)

    def _format_unresolved_payload(self, payload_line):
        label = (
            payload_line.get('product_name')
            or payload_line.get('flower_type')
            or _('Producto sin identificar')
        )
        return self._format_unresolved_item(label, payload_line.get('quantity') or 1)

    def _format_unresolved_item(self, label, quantity):
        return {
            'product_id': False,
            'product': _('Sin producto Odoo asociado: %s') % label,
            'required_qty': quantity,
            'available_qty': 0.0,
            'missing_qty': quantity,
            'uom': '',
        }

    def ensure_stock_payload_has_lines(self, payload):
        if not payload.get('order_id') and not payload.get('lines'):
            raise UserError(_('Debe enviar order_id o lines.'))

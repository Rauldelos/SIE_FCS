from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError


class ControlStockService(models.AbstractModel):
    _name = 'control.stock.service'
    _description = 'Reusable stock checker for products and kits'

    def check_products_stock(self, lines):
        requirements = self._build_requirements(lines)
        missing_items = []

        for product, required_qty in requirements.items():
            available_qty = product.free_qty
            if available_qty < required_qty:
                missing_items.append(self._format_missing_item(
                    product,
                    required_qty,
                    available_qty,
                ))

        return {
            'stock_ok': not missing_items,
            'missing_items': missing_items,
        }

    def consume_products_stock(self, lines, reference=False):
        requirements = self._build_requirements(lines)
        check_result = self.check_products_stock(lines)
        if not check_result['stock_ok']:
            return {
                'success': False,
                'stock_ok': False,
                'missing_items': check_result['missing_items'],
                'stock_move_ids': [],
            }

        if not requirements:
            return {
                'success': True,
                'stock_ok': True,
                'missing_items': [],
                'stock_move_ids': [],
            }

        source_location, destination_location = self._get_consumption_locations()
        moves = self.env['stock.move']
        move_name = reference or _('Consumo FCS')

        for product, required_qty in requirements.items():
            moves |= self.env['stock.move'].sudo().create({
                'name': move_name,
                'origin': reference or move_name,
                'product_id': product.id,
                'product_uom_qty': required_qty,
                'product_uom': product.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': destination_location.id,
            })

        moves._action_confirm()
        moves._action_assign()

        for move in moves:
            if 'quantity' in move._fields:
                move.quantity = move.product_uom_qty
            elif 'quantity_done' in move._fields:
                move.quantity_done = move.product_uom_qty

            for move_line in move.move_line_ids:
                done_qty = move_line.reserved_uom_qty or move.product_uom_qty
                if 'quantity' in move_line._fields:
                    move_line.quantity = done_qty
                elif 'qty_done' in move_line._fields:
                    move_line.qty_done = done_qty

        moves._action_done()

        return {
            'success': True,
            'stock_ok': True,
            'missing_items': [],
            'stock_move_ids': moves.ids,
        }

    def format_missing_items_message(self, missing_items):
        return '\n\n'.join(
            _(
                'Material: %(product)s\n'
                'Necesario: %(required).2f\n'
                'Disponible: %(available).2f\n'
                'Faltan: %(missing).2f'
            ) % {
                'product': item['product'],
                'required': item['required_qty'],
                'available': item['available_qty'],
                'missing': item['missing_qty'],
            }
            for item in missing_items
        )

    def _build_requirements(self, lines):
        requirements = defaultdict(float)

        for line in lines:
            product = self._resolve_product(line)
            quantity = self._resolve_quantity(line)
            if not product or quantity <= 0:
                continue

            bom = self._find_phantom_bom(product)
            if bom:
                multiplier = quantity / (bom.product_qty or 1.0)
                for component in bom.bom_line_ids:
                    requirements[component.product_id] += component.product_qty * multiplier
            else:
                requirements[product] += quantity

        return requirements

    def _resolve_product(self, line):
        product = line.get('product')
        if product:
            return product

        product_id = line.get('product_id')
        if product_id:
            product = self.env['product.product'].sudo().browse(int(product_id))
            return product if product.exists() else self.env['product.product']

        product_name = line.get('product_name')
        if product_name:
            return self.env['product.product'].sudo().search(
                [('name', 'ilike', product_name)],
                limit=1,
            )

        return self.env['product.product']

    def _resolve_quantity(self, line):
        return float(line.get('quantity') or line.get('product_uom_qty') or 0.0)

    def _find_phantom_bom(self, product):
        return self.env['mrp.bom'].sudo().search([
            ('type', '=', 'phantom'),
            '|',
            ('product_id', '=', product.id),
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
        ], limit=1)

    def _format_missing_item(self, product, required_qty, available_qty):
        missing_qty = required_qty - available_qty
        return {
            'product_id': product.id,
            'product': product.display_name,
            'required_qty': required_qty,
            'available_qty': available_qty,
            'missing_qty': missing_qty,
            'uom': product.uom_id.name,
        }

    def _get_consumption_locations(self):
        warehouse = self.env['stock.warehouse'].sudo().search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not warehouse:
            warehouse = self.env['stock.warehouse'].sudo().search([], limit=1)

        source_location = warehouse.lot_stock_id if warehouse else False
        if not source_location:
            source_location = self.env.ref(
                'stock.stock_location_stock',
                raise_if_not_found=False,
            )
        if not source_location:
            source_location = self.env['stock.location'].sudo().search([
                ('usage', '=', 'internal'),
            ], limit=1)

        destination_location = self.env.ref(
            'stock.stock_location_customers',
            raise_if_not_found=False,
        )
        if not destination_location:
            destination_location = self.env['stock.location'].sudo().search([
                ('usage', '=', 'customer'),
            ], limit=1)

        if not source_location or not destination_location:
            raise UserError(_(
                'No se han encontrado ubicaciones de stock para registrar la salida.'
            ))

        return source_location, destination_location

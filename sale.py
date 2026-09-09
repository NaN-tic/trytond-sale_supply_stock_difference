from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    @classmethod
    def _process_fulfillment(cls, sales):
        super()._process_fulfillment(sales)
        pool = Pool()
        Line = pool.get('sale.line')
        Move = pool.get('stock.move')
        Request = pool.get('purchase.request')

        lines = [line for sale in sales for line in sale.lines
            if (line.type == 'line' and line.product and line.quantity > 0
                and line.product.purchasable
                and line.product.supply_on_sale == 'stock_difference'
                and not getattr(line, 'drop_shipment', False)
                and sale.shipment_method != 'manual'
                and line.ready_for_supply and not line.purchase_request)]
        moves = [move for line in lines
            for move in line.get_stock_difference_moves()]
        if not moves:
            return

        # Reserve actual stock first, as production_supply does for inputs.
        # Reservations prevent another sale from reusing the same stock.
        Move.assign_try(moves)
        requests = []
        to_save = []
        with Transaction().set_context(_sale_supply_stock_difference=True):
            for line in Line.browse([line.id for line in lines]):
                request = line.get_purchase_request({})
                if request:
                    requests.append(request)
                    line.purchase_request = request
                    to_save.append(line)
            Request.save(requests)
            Line.save(to_save)


class Line(metaclass=PoolMeta):
    __name__ = 'sale.line'

    @property
    def supply_on_sale_drop_move(self):
        if (self.product
                and self.product.supply_on_sale == 'stock_difference'
                and not getattr(self, 'drop_shipment', False)):
            return False
        return super().supply_on_sale_drop_move

    def get_stock_difference_moves(self):
        Shipment = Pool().get('stock.shipment.out')
        moves = []
        for outgoing in self.moves:
            shipment = outgoing.shipment
            if (not isinstance(shipment, Shipment)
                    or shipment.state not in {'draft', 'waiting'}):
                continue
            if shipment.warehouse_storage == shipment.warehouse_output:
                candidates = [outgoing]
            else:
                candidates = [move for move in shipment.inventory_moves
                    if move.origin == outgoing]
            moves.extend(move for move in candidates
                if move.state == 'draft' and move.quantity > 0)
        return moves

    def get_purchase_request(self, product_quantities):
        if (not self.product
                or self.product.supply_on_sale != 'stock_difference'
                or getattr(self, 'drop_shipment', False)):
            return super().get_purchase_request(product_quantities)
        if (not Transaction().context.get('_sale_supply_stock_difference')
                or self.purchase_request or not self.ready_for_supply
                or not self.product.purchasable):
            return

        pool = Pool()
        Uom = pool.get('product.uom')
        Request = pool.get('purchase.request')
        unit = self.product.purchase_uom or self.product.default_uom
        quantity = sum(Uom.compute_qty(
                move.unit, move.quantity, unit, round=False)
            for move in self.get_stock_difference_moves())
        quantity = unit.ceil(quantity)
        if quantity <= 0:
            return
        supplier, purchase_date = Request.find_best_supplier(
            self.product, self.shipping_date,
            **self._get_purchase_request_product_supplier_pattern())
        return Request(
            product=self.product, party=supplier,
            quantity=quantity, unit=unit,
            computed_quantity=quantity, computed_unit=unit,
            purchase_date=purchase_date, supply_date=self.shipping_date,
            company=self.sale.company, warehouse=self.warehouse,
            origin=self.sale)

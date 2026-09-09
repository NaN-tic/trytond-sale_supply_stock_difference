import unittest
from datetime import timedelta
from decimal import Decimal

from proteus import Model
from trytond.modules.account_invoice.tests.tools import create_payment_term
from trytond.modules.company.tests.tools import create_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class TestScenarioStockDifference(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):
        config = activate_modules([
            'sale_supply_stock_difference', 'sale_supply_drop_shipment'],
            create_company)
        Template = Model.get('product.template')
        Uom = Model.get('product.uom')
        Party = Model.get('party.party')
        ProductSupplier = Model.get('purchase.product_supplier')
        Location = Model.get('stock.location')
        Inventory = Model.get('stock.inventory')
        InventoryLine = Model.get('stock.inventory.line')
        Sale = Model.get('sale.sale')
        Request = Model.get('purchase.request')
        unit, = Uom.find([('name', '=', 'Unit')])
        gram, = Uom.find([('name', '=', 'Gram')])
        kilogram, = Uom.find([('name', '=', 'Kilogram')])
        storage, = Location.find([('code', '=', 'STO')])
        warehouse, = Location.find([('code', '=', 'WH')])
        customer = Party(name='Customer')
        customer.save()
        supplier = Party(name='Supplier')
        supplier.save()
        payment_term = create_payment_term()
        payment_term.save()

        sales = []
        for name, stock, quantities, default_unit, sale_unit, expected in [
                ('Partial', 2, [5], unit, unit, [3]),
                ('Enough', 5, [3], unit, unit, []),
                ('Empty', 0, [4], unit, unit, [4]),
                ('Several lines', 5, [3, 4], unit, unit, [2]),
                ('Different units', 2000, [3], gram, kilogram, [1000]),
                ]:
            template = Template(name=name, type='goods',
                default_uom=default_unit, sale_uom=sale_unit,
                purchase_uom=default_unit, purchasable=True, salable=True,
                supply_on_sale='stock_difference', list_price=Decimal(1))
            template.save()
            product, = template.products
            ProductSupplier(template=template, party=supplier,
                lead_time=timedelta()).save()
            if stock:
                inventory = Inventory(location=storage)
                inventory.lines.append(InventoryLine(
                    product=product, quantity=stock))
                inventory.click('confirm')

            sale = Sale(party=customer, warehouse=warehouse,
                payment_term=payment_term, invoice_method='manual',
                shipment_method='order')
            for quantity in quantities:
                line = sale.lines.new()
                line.product = product
                line.quantity = quantity
            sale.click('quote')
            sale.click('confirm')
            sales.append(sale)
            requests = Request.find([('origin', '=', str(sale))])
            self.assertEqual(sorted(r.quantity for r in requests), expected)
            for request in requests:
                self.assertEqual(request.party, supplier)
                self.assertEqual(request.unit, default_unit)
                self.assertEqual(request.quantity, request.computed_quantity)
                self.assertEqual(request.warehouse, warehouse)
            reserved = sum(move.quantity for shipment in sale.shipments
                for move in shipment.inventory_moves
                if move.state == 'assigned')
            expected_reserved = min(stock, sum(quantities)
                * (1000 if default_unit == gram else 1))
            if default_unit == gram:
                reserved *= 1000
            self.assertEqual(reserved, expected_reserved)
            before = [r.id for r in requests]
            Sale.process([sale.id], config.context)
            self.assertEqual([r.id for r in Request.find([
                ('origin', '=', str(sale))])], before)

        # A second sale cannot reuse the stock reserved by the first one.
        first = sales[0]
        second = Sale(party=customer, warehouse=warehouse,
            payment_term=payment_term, invoice_method='manual',
            shipment_method='order')
        line = second.lines.new()
        line.product = first.lines[0].product
        line.quantity = 2
        second.click('quote')
        second.click('confirm')
        request, = Request.find([('origin', '=', str(second))])
        self.assertEqual(request.quantity, 2)

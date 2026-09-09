from trytond.pool import PoolMeta


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.supply_on_sale.selection.append(
            ('stock_difference', 'Purchase Only the Shortage'))


class TemplateSupplyOnSale(metaclass=PoolMeta):
    __name__ = 'product.template.supply_on_sale'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.supply_on_sale.selection.append(
            ('stock_difference', 'Purchase Only the Shortage'))

from trytond.pool import Pool

from . import product, sale


def register():
    Pool.register(
        product.Template,
        product.TemplateSupplyOnSale,
        sale.Sale,
        sale.Line,
        module='sale_supply_stock_difference', type_='model')

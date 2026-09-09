from setuptools import setup


setup(
    name='nantic_sale_supply_stock_difference',
    version='8.0.0',
    description='Reserve sale stock and purchase only the shortage',
    packages=['trytond.modules.sale_supply_stock_difference',
        'trytond.modules.sale_supply_stock_difference.tests'],
    package_dir={'trytond.modules.sale_supply_stock_difference': '.'},
    package_data={'trytond.modules.sale_supply_stock_difference':
        ['tryton.cfg', 'locale/*.po', 'README']},
    install_requires=['trytond>=8.0,<8.1', 'trytond_sale_supply>=8.0,<8.1'],
    entry_points={'trytond.modules': [
        'sale_supply_stock_difference = '
        'trytond.modules.sale_supply_stock_difference']})

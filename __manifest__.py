# -*- coding: utf-8 -*-
{
    'name': "Vertragsverwaltung",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Getronic Engineering AG",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'portal', 'stock','mrp','sale','q_note'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'security/contracts_security.xml',
        'security/ir.model.access.csv',
        #'report/sale_contract_reports.xml',
        #'report/lot_label_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'uninstall_hook': "uninstall_hook",
    'installable': True,
    'auto_install': False,
}
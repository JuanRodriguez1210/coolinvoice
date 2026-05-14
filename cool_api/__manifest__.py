# -*- coding: utf-8 -*-
{
    'name': "cool_api",

    'summary': "API REST para crear facturas en Odoo desde Coolinvoice",

    'description': """
Long description of module's purpose
    """,

    'author': "Coolinvoice",
    'website': "https://www.coolinvoice.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '18.0.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'account',
                'contacts',
                'portal',
                'website'
                ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        #'views/views.xml',
        'views/res_users_views.xml',
        'views/portal_invoice_templates.xml',
        "views/portal_invoice_form.xml",
        "views/portal_invoice_list.xml",
        'views/res_company_views.xml',
        'report/invoice_dian_report.xml',
        'report/invoice_dian_template.xml'
    ],

    "assets": {

        "web.assets_frontend": [
            "cool_api/static/src/css/portal_invoice.css",
            "cool_api/static/src/js/portal_invoice.js",
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}


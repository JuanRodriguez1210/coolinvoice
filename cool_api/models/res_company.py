from odoo import models, fields


class ResCompanyCool(models.Model):
    _inherit = 'res.company'

    cool_invoice_report_id = fields.Many2one(
        'ir.actions.report',
        string='Formato de factura',
        help='Reporte de factura para la compañía.',
    )
from odoo import http
from odoo import models, fields, api
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class CoolAPIController(http.Controller):

    @http.route('/api/create_invoice', type='json', auth='none', methods=['POST'], csrf=False)
    def create_invoice(self, **kwargs):
        company = request.env.company

        journal_id = kwargs.get('journal_id')
        currency_name = kwargs.get('currency_id')
        partner_id = kwargs.get('partner_id')
        lines = kwargs.get('lines')

        # Validaciones básicas
        if not partner_id or not lines:
            return {"error": "Missing partner_id or lines"}
        if not journal_id:
            return {"error": "Missing journal_id"}

        # Buscar la moneda
        currency = None
        if currency_name:
            currency = request.env['res.currency'].sudo().search([('name', '=', currency_name)], limit=1)
            if not currency:
                return {"error": f"Currency '{currency_name}' not found"}

        # Si no se envió moneda, usar la moneda de la compañía
        if not currency:
            if not company.currency_id:
                return {"error": "Company does not have a default currency"}
            currency = company.currency_id

        # Construir valores de las líneas, asegurando account_id
        invoice_lines = []
        for line in lines:
            account_id = line.get('account_id')
            if not account_id:
                return {"error": "Each line must have 'account_id'"}
            invoice_lines.append((0, 0, {
                'name': line.get('name', 'Invoice Line'),
                'quantity': line.get('quantity', 1),
                'price_unit': line.get('price_unit', 0.0),
                'account_id': account_id,
            }))

        # Valores de la factura
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'company_id': company.id,
            'journal_id': journal_id,
            'currency_id': currency.id,
            'invoice_line_ids': invoice_lines,
        }

        _logger.info(f"Creating invoice with values: {invoice_vals}")

        # Crear la factura con sudo()
        invoice = request.env['account.move'].sudo().create(invoice_vals)

        return {
            "success": True,
            "invoice_id": invoice.id,
            "name": invoice.name
        }


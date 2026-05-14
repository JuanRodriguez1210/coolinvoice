import json
import logging

from markupsafe import Markup

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import (
    CustomerPortal,
    pager as portal_pager,
)

_logger = logging.getLogger(__name__)

INVOICES_PER_PAGE = 10


class InvoicePortalController(CustomerPortal):

    # =========================================================
    # HOME PORTAL
    # =========================================================

    def _prepare_home_portal_values(self, counters):

        values = super()._prepare_home_portal_values(counters)

        if 'invoice_count' in counters:

            values['invoice_count'] = request.env[
                'account.move'
            ].sudo().search_count([
                ('portal_user_id', '=', request.env.user.id),
                ('move_type', '=', 'out_invoice'),
            ])

        return values

    # =========================================================
    # FORM VALUES
    # =========================================================

    def _get_portal_invoice_form_values(self):

        company = request.env.company

        journals = request.env['account.journal'].sudo().search([
            ('type', '=', 'sale'),
            ('company_id', '=', company.id),
        ])

        currencies = request.env['res.currency'].sudo().search([
            ('active', '=', True)
        ])

        accounts = request.env['account.account'].sudo().search([
            ('company_ids', 'in', company.id),
            ('account_type', 'in', ['income', 'income_other']),
            ('deprecated', '=', False),
        ])

        products = request.env['product.product'].sudo().search([
            ('sale_ok', '=', True),
            ('active', '=', True),
        ], order='name asc')

        partners = request.env['res.partner'].sudo().search([
            ('active', '=', True),
        ], order='name asc', limit=300)

        accounts_json = json.dumps([
            {
                'id': account.id,
                'name': f'{account.name} ({account.code})',
            }
            for account in accounts
        ])

        products_json = json.dumps([
            {
                'id': product.id,
                'name': product.name,
                'price': product.lst_price or 0,
                'acct': (
                    product.property_account_income_id.id
                    or product.categ_id.property_account_income_categ_id.id
                    or 0
                ),
            }
            for product in products
        ])

        return {

            # =================================================
            # NORMAL VALUES
            # =================================================

            'partner': request.env.user.partner_id,

            'company': company,

            'journals': journals,

            'currencies': currencies,

            'accounts': accounts,

            'products': products,

            'partners': partners,

            'default_currency': company.currency_id,

            'page_name': 'create_invoice',

            # =================================================
            # JSON SERIALIZED
            # =================================================

            'accounts_json': Markup(accounts_json),

            'products_json': Markup(products_json),
        }

    # =========================================================
    # GET COMPANY REPORT
    # =========================================================

    def _get_invoice_report(self, invoice):

        company = invoice.company_id

        # =====================================================
        # CUSTOM REPORT BY COMPANY
        # =====================================================

        if company.cool_invoice_report_id:

            return company.cool_invoice_report_id

        # =====================================================
        # FALLBACK ODOO REPORT
        # =====================================================

        return request.env.ref('account.account_invoices')

    # =========================================================
    # BUILD PDF URL
    # =========================================================

    def _build_invoice_print_url(self, invoice):

        return f'/my/invoices/{invoice.id}/print'

    # =========================================================
    # PRINT INVOICE
    # =========================================================

    @http.route(
        '/my/invoices/<int:invoice_id>/print',
        type='http',
        auth='user',
        website=True
    )
    def portal_print_invoice(self, invoice_id, **kwargs):

        invoice = request.env[
            'account.move'
        ].sudo().browse(invoice_id)

        if not invoice.exists():

            return request.not_found()

        # =====================================================
        # SECURITY
        # =====================================================

        if invoice.portal_user_id.id != request.env.user.id:

            return request.not_found()

        report = self._get_invoice_report(invoice)

        pdf_content, _ = request.env[
            'ir.actions.report'
        ].sudo()._render_qweb_pdf(
            report.report_name,
            invoice.id
        )

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            (
                'Content-Length',
                len(pdf_content)
            ),
        ]

        return request.make_response(
            pdf_content,
            headers=pdfhttpheaders
        )

    # =========================================================
    # INVOICE LIST
    # =========================================================

    @http.route(
        '/my/invoices',
        type='http',
        auth='user',
        website=True,
        methods=['GET']
    )
    def portal_invoice_list(self, page=1, **kwargs):

        domain = [
            ('portal_user_id', '=', request.env.user.id),
            ('move_type', '=', 'out_invoice'),
        ]

        total = request.env['account.move'].sudo().search_count(domain)

        pager = portal_pager(
            url='/my/invoices',
            total=total,
            page=int(page),
            step=INVOICES_PER_PAGE,
        )

        invoices = request.env['account.move'].sudo().search(
            domain,
            order='invoice_date desc, id desc',
            limit=INVOICES_PER_PAGE,
            offset=pager['offset'],
        )

        invoice_print_urls = {
            inv.id: self._build_invoice_print_url(inv)
            for inv in invoices
        }

        return request.render(
            'cool_api.portal_invoice_list',
            {
                'invoices': invoices,
                'invoice_print_urls': invoice_print_urls,
                'pager': pager,
                'page_name': 'my_invoices',
            }
        )

    # =========================================================
    # GET FORM
    # =========================================================

    @http.route(
        '/my/invoices/create',
        type='http',
        auth='user',
        website=True,
        methods=['GET']
    )
    def portal_invoice_create_form(self, **kwargs):

        values = self._get_portal_invoice_form_values()

        values.update({

            'error': kwargs.get('error'),

            'success': kwargs.get('success'),

            'success_name': kwargs.get(
                'success_name',
                ''
            ),

            'success_print_url': kwargs.get(
                'success_print_url',
                ''
            ),
        })

        return request.render(
            'cool_api.portal_create_invoice',
            values
        )

    # =========================================================
    # POST CREATE
    # =========================================================

    @http.route(
        '/my/invoices/create',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True
    )
    def portal_invoice_create_submit(self, **kw):

        company = request.env.company

        current_user = request.env.user

        # =====================================================
        # PARTNER
        # =====================================================

        partner_id_raw = kw.get('partner_id')

        if partner_id_raw:

            partner = request.env[
                'res.partner'
            ].sudo().browse(int(partner_id_raw))

            if not partner.exists():

                return request.redirect(
                    '/my/invoices/create?error=invalid_partner'
                )

        else:

            partner = current_user.partner_id

        # =====================================================
        # MAIN DATA
        # =====================================================

        journal_id = kw.get('journal_id')

        currency_id = kw.get('currency_id')

        if not journal_id:

            return request.redirect(
                '/my/invoices/create?error=missing_journal'
            )

        # =====================================================
        # LINES
        # =====================================================

        invoice_lines = []

        idx = 0

        while f'line_account_{idx}' in kw:

            account_id = kw.get(f'line_account_{idx}')

            name = kw.get(
                f'line_name_{idx}',
                'Línea de factura'
            )

            qty = float(
                kw.get(f'line_qty_{idx}') or 1
            )

            price = float(
                kw.get(f'line_price_{idx}') or 0.0
            )

            product_id = kw.get(f'line_product_{idx}')

            if not account_id:

                return request.redirect(
                    '/my/invoices/create?error=missing_account'
                )

            line_vals = {

                'name': name,

                'quantity': qty,

                'price_unit': price,

                'account_id': int(account_id),
            }

            if product_id:

                line_vals['product_id'] = int(product_id)

            invoice_lines.append((0, 0, line_vals))

            idx += 1

        if not invoice_lines:

            return request.redirect(
                '/my/invoices/create?error=no_lines'
            )

        # =====================================================
        # CURRENCY
        # =====================================================

        currency = None

        if currency_id:

            currency = request.env[
                'res.currency'
            ].sudo().browse(int(currency_id))

        if not currency or not currency.exists():

            currency = company.currency_id

        # =====================================================
        # CREATE
        # =====================================================

        try:

            invoice = request.env[
                'account.move'
            ].sudo().create({

                'move_type': 'out_invoice',

                'partner_id': partner.id,

                'company_id': company.id,

                'journal_id': int(journal_id),

                'currency_id': currency.id,

                'invoice_line_ids': invoice_lines,

                'portal_user_id': current_user.id,
            })

            # ================================================
            # POST INVOICE
            # ================================================

            invoice.action_post()

            _logger.info(
                "Portal invoice posted: %s (id=%s) by portal user %s",
                invoice.name,
                invoice.id,
                current_user.login,
            )

        except Exception as exc:

            _logger.exception(
                "Error creating portal invoice: %s",
                exc
            )

            return request.redirect(
                '/my/invoices/create?error=server_error'
            )

        # =====================================================
        # SUCCESS
        # =====================================================

        print_url = self._build_invoice_print_url(invoice)

        return request.redirect(

            f'/my/invoices/create'
            f'?success={invoice.id}'
            f'&success_name={invoice.name}'
            f'&success_print_url={print_url}'
        )
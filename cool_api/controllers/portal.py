from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
import logging

_logger = logging.getLogger(__name__)

INVOICES_PER_PAGE = 10


class InvoicePortalController(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'invoice_count' in counters:
            values['invoice_count'] = request.env['account.move'].sudo().search_count([('portal_user_id', '=', request.env.user.id),
                                                                                       ('move_type', '=', 'out_invoice'),])
        return values

    def _get_portal_invoice_form_values(self):
        company = request.env.company

        journals = request.env['account.journal'].sudo().search([
            ('type', '=', 'sale'),
            ('company_id', '=', company.id),
        ])
        currencies = request.env['res.currency'].sudo().search([('active', '=', True)])

        # Odoo 18: company_ids en lugar de company_id
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

        return {
            'partner': request.env.user.partner_id,
            'company': company,
            'journals': journals,
            'currencies': currencies,
            'accounts': accounts,
            'products': products,
            'partners': partners,
            'default_currency': company.currency_id,
            'page_name': 'create_invoice',
        }

    # ── Listado /my/invoices ──────────────────────────────────────────────────

    @http.route('/my/invoices', type='http', auth='user', website=True, methods=['GET'])
    def portal_invoice_list(self, page=1, **kwargs):
        domain = [('portal_user_id', '=', request.env.user.id),
                  ('move_type', '=', 'out_invoice'),]

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
            inv.id: f'/report/pdf/account.report_invoice/{inv.id}'
            for inv in invoices
        }

        return request.render('cool_api.portal_invoice_list', {
            'invoices': invoices,
            'invoice_print_urls': invoice_print_urls,
            'pager': pager,
            'page_name': 'my_invoices',
        })

    # ── GET formulario ────────────────────────────────────────────────────────

    @http.route('/my/invoices/create', type='http', auth='user', website=True, methods=['GET'])
    def portal_invoice_create_form(self, **kwargs):
        values = self._get_portal_invoice_form_values()
        values['error'] = kwargs.get('error')
        values['success'] = kwargs.get('success')
        values['success_name'] = kwargs.get('success_name', '')
        values['success_print_url'] = kwargs.get('success_print_url', '')
        return request.render('cool_api.portal_create_invoice', values)

    # ── POST crear factura ────────────────────────────────────────────────────

    @http.route('/my/invoices/create', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_invoice_create_submit(self, **kw):
        company = request.env.company
        current_user = request.env.user

        # Cliente seleccionado o el del usuario actual
        partner_id_raw = kw.get('partner_id')
        if partner_id_raw:
            partner = request.env['res.partner'].sudo().browse(int(partner_id_raw))
            if not partner.exists():
                return request.redirect('/my/invoices/create?error=invalid_partner')
        else:
            partner = current_user.partner_id

        journal_id  = kw.get('journal_id')
        currency_id = kw.get('currency_id')

        if not journal_id:
            return request.redirect('/my/invoices/create?error=missing_journal')

        invoice_lines = []
        idx = 0
        while f'line_account_{idx}' in kw:
            account_id = kw.get(f'line_account_{idx}')
            name       = kw.get(f'line_name_{idx}', 'Línea de factura')
            qty        = float(kw.get(f'line_qty_{idx}')   or 1)
            price      = float(kw.get(f'line_price_{idx}') or 0.0)
            product_id = kw.get(f'line_product_{idx}')

            if not account_id:
                return request.redirect('/my/invoices/create?error=missing_account')

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
            return request.redirect('/my/invoices/create?error=no_lines')

        currency = None
        if currency_id:
            currency = request.env['res.currency'].sudo().browse(int(currency_id))
        if not currency or not currency.exists():
            currency = company.currency_id

        try:
            invoice = request.env['account.move'].sudo().create({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'company_id': company.id,
                'journal_id': int(journal_id),
                'currency_id': currency.id,
                'invoice_line_ids': invoice_lines,
                'portal_user_id': current_user.id,
            })
            invoice.action_post()
            _logger.info("Portal invoice posted: %s (id=%s) by portal user %s",
                         invoice.name, invoice.id, current_user.login)
        except Exception as exc:
            _logger.exception("Error creating portal invoice: %s", exc)
            return request.redirect('/my/invoices/create?error=server_error')

        print_url = f'/report/pdf/account.report_invoice/{invoice.id}'
        return request.redirect(
            f'/my/invoices/create'
            f'?success={invoice.id}'
            f'&success_name={invoice.name}'
            f'&success_print_url={print_url}'
        )
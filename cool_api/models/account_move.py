# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountMovePortal(models.Model):
    """Extiende account.move para registrar el usuario de portal que creó la factura."""
    _inherit = 'account.move'

    portal_user_id = fields.Many2one(
        'res.users',
        string='Creado por (Portal)',
        readonly=True,
        copy=False,
        index=True,
        help="Usuario de portal que generó esta factura desde el sitio web.",
    )
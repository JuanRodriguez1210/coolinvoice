from odoo import models, fields
import secrets

class ResUsers(models.Model):
    _inherit = 'res.users'

    api_token = fields.Char(string='API Token',
                            readonly=True,
                            copy=False,
                            store=True,
                            help="Token de autenticación para la API REST. Generado automáticamente al crear el usuario.")

    def generate_api_token(self):
        for user in self:
            user.api_token = secrets.token_hex(16)

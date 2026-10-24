from pathlib import Path

from odoo import api, fields, models
from odoo.modules.module import get_module_path
from odoo.tools.binary import BinaryBytes


class HotelProperty(models.Model):
    _name = 'hotel.property'
    _description = 'Hotel'

    name = fields.Char(required=True)
    phone = fields.Char()
    email = fields.Char()
    street = fields.Char(string='Address')

    def _fixed_logo(self):
        path = Path(get_module_path('hotel_management')) / 'static' / 'src' / 'img' / 'logo.png'
        return path.read_bytes()

    def _sync_company_name(self):
        logo = BinaryBytes(self._fixed_logo())
        for hotel in self:
            company = self.env.company.sudo()
            if hotel.name and company.partner_id.name != hotel.name:
                company.partner_id.name = hotel.name
            if bytes(company.logo) != logo.content:
                company.logo = logo

    @api.model
    def _register_hook(self):
        res = super()._register_hook()
        hotel = self.sudo().search([], limit=1)
        if hotel:
            hotel._sync_company_name()
        return res

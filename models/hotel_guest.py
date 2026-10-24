from odoo import fields, models


class HotelGuest(models.Model):
    _name = 'hotel.guest'
    _description = 'Hotel Guest'
    _order = 'name'

    name = fields.Char(required=True)
    phone = fields.Char()
    email = fields.Char()
    id_number = fields.Char(string='ID / Passport')
    active = fields.Boolean(default=True)
    booking_ids = fields.One2many('hotel.booking', 'guest_id', string='Bookings')

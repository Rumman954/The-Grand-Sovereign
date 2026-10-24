from datetime import timedelta

from odoo import api, fields, models


class HotelAvailability(models.TransientModel):
    _name = 'hotel.availability'
    _description = 'Room Availability'

    check_in = fields.Date(
        string='Check In',
        required=True,
        default=fields.Date.context_today,
    )
    check_out = fields.Date(
        string='Check Out',
        required=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=1),
    )
    room_ids = fields.Many2many(
        'hotel.room',
        compute='_compute_room_ids',
        string='Free Rooms',
    )
    room_count = fields.Integer(compute='_compute_room_ids')
    single_count = fields.Integer(string='Single', compute='_compute_room_ids')
    double_count = fields.Integer(string='Double', compute='_compute_room_ids')
    deluxe_count = fields.Integer(string='Deluxe', compute='_compute_room_ids')
    suite_count = fields.Integer(string='Suite', compute='_compute_room_ids')

    @api.depends('check_in', 'check_out')
    def _compute_room_ids(self):
        for wizard in self:
            rooms = self.env['hotel.room']._free_for_dates(wizard.check_in, wizard.check_out)
            wizard.room_ids = rooms
            wizard.room_count = len(rooms)
            wizard.single_count = len(rooms.filtered(lambda room: room.room_type == 'single'))
            wizard.double_count = len(rooms.filtered(lambda room: room.room_type == 'double'))
            wizard.deluxe_count = len(rooms.filtered(lambda room: room.room_type == 'deluxe'))
            wizard.suite_count = len(rooms.filtered(lambda room: room.room_type == 'suite'))

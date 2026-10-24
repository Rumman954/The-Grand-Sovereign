import base64
from datetime import timedelta
from pathlib import Path

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_path

# Fixed print logo. Do not replace or ask for another one.
_PRINT_LOGO_SRC = None


def _print_logo_src():
    global _PRINT_LOGO_SRC
    if _PRINT_LOGO_SRC is None:
        path = Path(get_module_path('hotel_management')) / 'static' / 'src' / 'img' / 'logo.png'
        encoded = base64.b64encode(path.read_bytes()).decode()
        _PRINT_LOGO_SRC = 'data:image/png;base64,' + encoded
    return _PRINT_LOGO_SRC


class HotelBooking(models.Model):
    _name = 'hotel.booking'
    _description = 'Hotel Booking'
    _order = 'check_in desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
    )
    guest_id = fields.Many2one('hotel.guest', string='Guest', required=True)
    guest_phone = fields.Char(related='guest_id.phone', string='Phone', readonly=False)
    guest_email = fields.Char(related='guest_id.email', string='Email', readonly=False)
    guest_id_number = fields.Char(
        related='guest_id.id_number',
        string='NID / Passport',
        readonly=False,
    )
    room_id = fields.Many2one('hotel.room', string='Room', required=True)
    room_type = fields.Selection(related='room_id.room_type', string='Room Type')
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
    nights = fields.Integer(compute='_compute_nights', store=True)
    price_per_night = fields.Float(string='Price per Night')
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amount_total',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('checked_in', 'Checked In'),
            ('checked_out', 'Checked Out'),
            ('cancelled', 'Cancelled'),
        ],
        required=True,
        default='draft',
        copy=False,
    )
    notes = fields.Text()
    hotel_name = fields.Char(compute='_compute_hotel_name')
    slip_logo = fields.Char(compute='_compute_slip_logo')
    checked_in_at = fields.Datetime(string='Checked In At', readonly=True, copy=False)
    memo_issue_time = fields.Char(compute='_compute_memo_times')
    memo_check_in_time = fields.Char(compute='_compute_memo_times')
    memo_time_label = fields.Char(compute='_compute_memo_times')
    memo_arrival = fields.Char(string='Arrival time', compute='_compute_memo_times')
    memo_check_out_time = fields.Char(compute='_compute_memo_times')
    available_room_ids = fields.Many2many(
        'hotel.room',
        compute='_compute_available_room_ids',
        string='Available Rooms',
    )

    @api.depends_context('uid')
    def _compute_hotel_name(self):
        hotel = self.env['hotel.property'].sudo().search([], limit=1)
        name = hotel.name or 'The Grand Sovereign'
        for booking in self:
            booking.hotel_name = name

    def _compute_slip_logo(self):
        src = _print_logo_src()
        for booking in self:
            booking.slip_logo = src

    def _clock(self, moment):
        local = fields.Datetime.context_timestamp(self, moment)
        clock = local.strftime('%I:%M %p').lstrip('0')
        return clock

    def _compute_memo_times(self):
        issued = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        issued_text = issued.strftime('%d %B %Y, %I:%M %p').replace(' 0', ' ')
        for booking in self:
            if booking.checked_in_at:
                booking.memo_time_label = 'Checked in'
                booking.memo_check_in_time = booking._clock(booking.checked_in_at)
            elif booking.create_date:
                booking.memo_time_label = 'Booked at'
                booking.memo_check_in_time = booking._clock(booking.create_date)
            else:
                booking.memo_time_label = 'Booked at'
                booking.memo_check_in_time = ''
            booking.memo_check_out_time = '11:00 AM'
            booking.memo_issue_time = issued_text
            booking.memo_arrival = f'{booking.memo_time_label} {booking.memo_check_in_time}'.strip()

    @api.depends('check_in', 'check_out', 'room_id')
    def _compute_available_room_ids(self):
        for booking in self:
            free = self.env['hotel.room']._free_for_dates(
                booking.check_in,
                booking.check_out,
                booking._origin.ids,
            )
            booking.available_room_ids = free

    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for booking in self:
            if booking.check_in and booking.check_out and booking.check_out > booking.check_in:
                booking.nights = (booking.check_out - booking.check_in).days
            else:
                booking.nights = 0

    @api.depends('nights', 'price_per_night')
    def _compute_amount_total(self):
        for booking in self:
            booking.amount_total = booking.nights * booking.price_per_night

    @api.onchange('room_id')
    def _onchange_room_id(self):
        if self.room_id:
            self.price_per_night = self.room_id.price_per_night

    @api.onchange('room_id', 'check_in', 'check_out')
    def _onchange_room_taken(self):
        if not self.room_id or not self.check_in or not self.check_out:
            return
        free = self.env['hotel.room']._free_for_dates(
            self.check_in,
            self.check_out,
            self._origin.ids,
        )
        if self.room_id not in free:
            return {
                'warning': {
                    'title': 'Room unavailable',
                    'message': (
                        f'Room {self.room_id.number} is already booked for these dates.'
                    ),
                }
            }

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for booking in self:
            if booking.check_in and booking.check_out and booking.check_out <= booking.check_in:
                raise ValidationError('Check-out must be after check-in.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.booking') or 'New'
            if not vals.get('price_per_night') and vals.get('room_id'):
                room = self.env['hotel.room'].browse(vals['room_id'])
                vals['price_per_night'] = room.price_per_night
        return super().create(vals_list)

    def _ensure_can_book_room(self):
        for booking in self:
            if booking.state in ('checked_out', 'cancelled') or not booking.room_id:
                continue
            room = booking.room_id
            if room.state == 'maintenance':
                raise ValidationError(f'Room {room.number} is under maintenance.')
            clash = self.search([
                ('id', '!=', booking.id),
                ('room_id', '=', room.id),
                ('state', 'in', ('draft', 'confirmed', 'checked_in')),
                ('check_in', '<', booking.check_out),
                ('check_out', '>=', booking.check_in),
            ], limit=1)
            if clash:
                raise ValidationError(
                    f'Room {room.number} is already booked from '
                    f'{clash.check_in} to {clash.check_out} ({clash.name}). '
                    'Check that guest out before booking this room again.'
                )

    @api.constrains('room_id', 'check_in', 'check_out', 'state')
    def _check_room_free(self):
        self._ensure_can_book_room()

    def _release_room_if_empty(self):
        for booking in self:
            still_in = self.search_count([
                ('room_id', '=', booking.room_id.id),
                ('state', '=', 'checked_in'),
                ('id', '!=', booking.id),
            ])
            if not still_in and booking.room_id.state == 'occupied':
                booking.room_id.state = 'dirty'

    def action_confirm(self):
        for booking in self:
            if booking.state != 'draft':
                raise UserError('Only a draft booking can be confirmed.')
            booking._ensure_can_book_room()
            booking.state = 'confirmed'
        return self.action_print_slip()

    def action_print_slip(self):
        return self.env.ref(
            'hotel_management.action_report_booking_slip'
        ).report_action(self)

    def action_check_in(self):
        for booking in self:
            if booking.state != 'confirmed':
                raise UserError('Confirm the booking before check-in.')
            booking._ensure_can_book_room()
            if booking.room_id.state == 'dirty':
                raise UserError(
                    f'Room {booking.room_id.number} is dirty. '
                    'Mark it available after cleaning.'
                )
            if booking.room_id.state == 'occupied':
                raise UserError(f'Room {booking.room_id.number} is already occupied.')
            booking.room_id.state = 'occupied'
            booking.checked_in_at = fields.Datetime.now()
            booking.state = 'checked_in'

    def action_check_out(self):
        for booking in self:
            if booking.state != 'checked_in':
                raise UserError('Only a checked-in guest can be checked out.')
            booking.state = 'checked_out'
            booking._release_room_if_empty()

    def action_cancel(self):
        for booking in self:
            if booking.state in ('checked_out', 'cancelled'):
                raise UserError('This booking cannot be cancelled.')
            was_checked_in = booking.state == 'checked_in'
            booking.state = 'cancelled'
            if was_checked_in:
                booking._release_room_if_empty()

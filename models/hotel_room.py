from odoo import api, fields, models


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'
    _order = 'number'
    _rec_name = 'number'

    number = fields.Char(string='Room Number', required=True)
    room_type = fields.Selection(
        selection=[
            ('single', 'Single'),
            ('double', 'Double'),
            ('deluxe', 'Deluxe'),
            ('suite', 'Suite'),
        ],
        string='Type',
        required=True,
        default='single',
    )
    floor = fields.Integer(default=1)
    capacity = fields.Integer(default=1)
    price_per_night = fields.Float(string='Price per Night', required=True)
    state = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('occupied', 'Occupied'),
            ('dirty', 'Dirty'),
            ('maintenance', 'Maintenance'),
        ],
        string='Status',
        required=True,
        default='available',
    )
    active = fields.Boolean(default=True)
    booking_ids = fields.One2many('hotel.booking', 'room_id', string='Bookings')
    availability_label = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('unavailable', 'Unavailable'),
        ],
        string='Availability',
        compute='_compute_availability_label',
    )

    _number_unique = models.Constraint(
        'unique (number)',
        'This room number already exists.',
    )

    @api.model
    def _free_for_dates(self, check_in, check_out, ignore_booking_ids=None):
        """Rooms with no open stay covering these dates, including checkout day."""
        if not check_in or not check_out or check_out <= check_in:
            return self.browse()
        domain = [
            ('state', 'in', ('draft', 'confirmed', 'checked_in')),
            ('check_in', '<', check_out),
            ('check_out', '>=', check_in),
        ]
        if ignore_booking_ids:
            domain.append(('id', 'not in', list(ignore_booking_ids)))
        booked = self.env['hotel.booking'].search(domain)
        return self.search([
            ('id', 'not in', booked.room_id.ids),
            ('state', '!=', 'maintenance'),
        ])

    @api.depends_context('booking_check_in', 'booking_check_out', 'booking_ignore_id')
    def _compute_availability_label(self):
        check_in = fields.Date.to_date(self.env.context.get('booking_check_in') or False)
        check_out = fields.Date.to_date(self.env.context.get('booking_check_out') or False)
        ignore = self.env.context.get('booking_ignore_id')
        booked_ids = set()
        if check_in and check_out and check_out > check_in and self.ids:
            domain = [
                ('room_id', 'in', self.ids),
                ('state', 'in', ('draft', 'confirmed', 'checked_in')),
                ('check_in', '<', check_out),
                ('check_out', '>=', check_in),
            ]
            if isinstance(ignore, int):
                domain.append(('id', '!=', ignore))
            booked_ids = set(self.env['hotel.booking'].search(domain).room_id.ids)
        for room in self:
            if room.state == 'maintenance' or room.id in booked_ids:
                room.availability_label = 'unavailable'
            else:
                room.availability_label = 'available'

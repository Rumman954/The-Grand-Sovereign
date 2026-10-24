{
    'name': 'The Grand Sovereign',
    'version': '1.1',
    'summary': 'Front desk for The Grand Sovereign',
    'description': """
Front desk for The Grand Sovereign: rooms, guests, bookings,
and a printable guest slip.
    """,
    'category': 'Services',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.access.csv',
        'data/ir_sequence.xml',
        'data/hotel_property.xml',
        'report/booking_slip.xml',
        'views/hotel_room_views.xml',
        'views/hotel_guest_views.xml',
        'views/hotel_booking_views.xml',
        'views/hotel_availability_views.xml',
        'views/hotel_menus.xml',
    ],
    'demo': [
        'demo/hotel_demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

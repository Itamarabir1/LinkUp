# app/core/admin_setup.py
from sqladmin import Admin

from app.admin_config import BookingAdmin, RequestAdmin, RideAdmin, UserAdmin


def setup_admin(app, engine):
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(RequestAdmin)
    admin.add_view(RideAdmin)
    admin.add_view(BookingAdmin)
    return admin

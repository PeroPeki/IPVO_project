"""Flask blueprintovi — svaki modul pokriva jedno API područje."""

from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.clubs import clubs_bp
from routes.events import events_bp
from routes.floor_maps import floor_maps_bp
from routes.hostess import hostess_bp
from routes.menu import menu_bp
from routes.orders import orders_bp
from routes.reservations import reservations_bp
from routes.tickets import tickets_bp

ALL_BLUEPRINTS = [
    auth_bp,
    clubs_bp,
    events_bp,
    tickets_bp,
    hostess_bp,
    floor_maps_bp,
    reservations_bp,
    menu_bp,
    orders_bp,
    admin_bp,
]

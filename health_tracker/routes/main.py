from __future__ import annotations

from health_tracker.routes.api import register_api_routes
from health_tracker.routes.auth import register_auth_routes
from health_tracker.routes.calendar import register_calendar_routes
from health_tracker.routes.settings import register_settings_routes
from health_tracker.routes.summaries import register_summary_routes
from health_tracker.routes.today_actions import register_today_action_routes
from health_tracker.routes.data import register_data_routes
from health_tracker.routes.entries import register_entry_routes
from health_tracker.routes.home import register_home_routes
from health_tracker.routes.meal_pages import register_meal_page_routes
from health_tracker.routes.programs import register_program_routes
from health_tracker.routes.records import register_record_routes


def register_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)
    register_auth_routes(app, ctx)
    register_settings_routes(app, ctx)
    register_home_routes(app, globals())
    register_summary_routes(app, globals())
    register_calendar_routes(app, globals())
    register_meal_page_routes(app, globals())

    from health_tracker.routes.auxiliary import register_aux_routes
    from health_tracker.routes.admin import register_admin_routes

    register_aux_routes(app, globals())
    register_admin_routes(app, globals())

    register_today_action_routes(app, globals())

    register_record_routes(app, globals())
    register_program_routes(app, globals())

    register_data_routes(app, globals())

    register_entry_routes(app, globals())
    register_api_routes(app, globals())


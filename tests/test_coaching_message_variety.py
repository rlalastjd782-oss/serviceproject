from __future__ import annotations

import re

import app as app_module

from health_tracker.date_utils import shift_date
from health_tracker.services.coaching import (
    list_daily_coaching_from_db,
    list_recovery_recommendations_from_db,
    save_recovery_checkin_to_db,
)
from tests.flow_base import FlowTestBase

UNRESOLVED_PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


class CoachingMessageVarietyTest(FlowTestBase):
    """Regression: the coaching message pools were changed from single fixed
    strings to random.choice(...) pools, some formatted with .format(...). A
    typo'd placeholder name (e.g. {parts} in the template but formatted with a
    different kwarg) would silently leave a literal "{parts}" in the message
    instead of raising, since only some pool entries use each placeholder.
    Sample repeatedly to exercise every branch and assert no message is ever
    empty or contains an unresolved {placeholder}.
    """

    def test_daily_coaching_messages_never_contain_unresolved_placeholders(self) -> None:
        with self.app.app_context():
            db = app_module.get_db()
            for condition, sleep, soreness, fatigue in (
                (5, 5, 1, 1),
                (1, 1, 5, 5),
                (3, 3, 3, 3),
                (3, 3, 5, 3),
            ):
                save_recovery_checkin_to_db(db, "2026-06-10", condition, sleep, soreness, fatigue, "")
                for _ in range(30):
                    messages = list_daily_coaching_from_db(db, "2026-06-10", shift_date)
                    for message in messages:
                        self.assertTrue(message)
                        self.assertNotRegex(message, UNRESOLVED_PLACEHOLDER)

    def test_recovery_recommendations_never_contain_unresolved_placeholders(self) -> None:
        with self.app.app_context():
            db = app_module.get_db()
            for _ in range(30):
                messages = list_recovery_recommendations_from_db(db, "2026-06-10", shift_date)
                for message in messages:
                    self.assertTrue(message)
                    self.assertNotRegex(message, UNRESOLVED_PLACEHOLDER)

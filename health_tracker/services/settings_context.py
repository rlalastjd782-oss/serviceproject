from __future__ import annotations


def build_settings_context(args, deps: dict[str, object]) -> dict[str, object]:
    return {
        "active_page": "settings",
        "error": args.get("error", ""),
        "sample_counts": deps["get_sample_data_counts"](),
        "data_counts": deps["get_data_counts"](),
        "backup_status": deps["get_backup_status"](),
        "data_safety_status": deps["get_data_safety_status"](),
        "health_status": deps["get_app_health_status"](),
        "reminder_settings": deps["list_reminder_settings"](),
        "has_settings_password": deps["has_settings_password"](),
        "qa_dummy_status": deps["get_qa_dummy_status"](),
        "app_preferences": deps["get_app_preferences"](),
        "accounts": deps["account_options"](),
        "current_account": deps["current_account"](),
    }

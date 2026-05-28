from __future__ import annotations

import json

from flask import Response, redirect, request, url_for


def register_data_routes(app, ctx: dict[str, object]) -> None:
    globals().update(ctx)

    @app.get("/export.json")
    def export_json():
        payload = export_all_data()
        return Response(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=health-tracker-export.json"},
        )

    @app.get("/export.csv")
    def export_csv():
        return Response(
            export_workout_csv(),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=health-tracker-workouts.csv"},
        )

    @app.get("/export-meals.csv")
    def export_meal_csv_route():
        return Response(
            export_meal_csv(),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=health-tracker-meals.csv"},
        )

    @app.get("/export/yearly.json")
    def export_yearly_json_route():
        year = normalize_year(request.args.get("year"), current_local_date())
        return Response(
            json.dumps(export_yearly_payload(year), ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=health-tracker-{year}.json"},
        )

    @app.get("/export/yearly-workouts.csv")
    def export_yearly_workouts_csv_route():
        year = normalize_year(request.args.get("year"), current_local_date())
        return Response(
            export_yearly_workout_csv(year),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=health-tracker-workouts-{year}.csv"},
        )

    @app.get("/export/yearly-meals.csv")
    def export_yearly_meals_csv_route():
        year = normalize_year(request.args.get("year"), current_local_date())
        return Response(
            export_yearly_meal_csv(year),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=health-tracker-meals-{year}.csv"},
        )

    @app.post("/import.json")
    def import_json():
        file = request.files.get("backup_file")
        if file and request.form.get("confirm_restore", "").strip() == "복원":
            import_all_data(json.loads(file.read().decode("utf-8")))
        return redirect(url_for("settings_page"))

    @app.post("/samples/delete")
    def delete_sample_data_route():
        if request.form.get("confirm_sample_delete", "").strip() == "샘플삭제":
            delete_sample_data()
        return redirect(url_for("settings_page"))

    @app.post("/samples/may")
    def create_may_sample_data_route():
        create_may_sample_data()
        return redirect(url_for("settings_page"))

    @app.post("/data/delete-all")
    def delete_all_data_route():
        if request.form.get("confirm_delete_all", "").strip() == "전체삭제":
            delete_all_data()
        return redirect(url_for("settings_page"))


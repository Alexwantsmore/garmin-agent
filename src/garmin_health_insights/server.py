"""Local web server for the Garmin Health Insights UI."""

from __future__ import annotations

import json
import mimetypes
from dataclasses import asdict
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any
from urllib.parse import unquote, urlparse

from garmin_health_insights.analyzer import HealthAnalyzer
from garmin_health_insights.models import DailyMetrics, InsightReport

MAX_REQUEST_BYTES = 2 * 1024 * 1024


def build_report_payload(payload: Any) -> dict[str, Any]:
    """Build a JSON-serializable report payload from browser/API input."""

    records, target_day, baseline_days = _extract_request_parts(payload)
    metrics = [DailyMetrics.from_mapping(record) for record in records]
    report = HealthAnalyzer(baseline_days=baseline_days).analyze(metrics, target_day=target_day)
    return _report_to_payload(report)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the local UI server until interrupted."""

    server = ThreadingHTTPServer((host, port), InsightHttpHandler)
    url = f"http://{host}:{server.server_port}"
    print(f"Garmin Health Insights UI: {url}")
    print("Wgraj plik JSON przygotowany z Garmin Connect albo użyj danych demo.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nZatrzymuję serwer.")
    finally:
        server.server_close()


class InsightHttpHandler(BaseHTTPRequestHandler):
    """HTTP handler serving static UI and report API."""

    server_version = "GarminHealthInsights/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/"):
            self._send_json({"error": "Unknown API endpoint."}, status=HTTPStatus.NOT_FOUND)
            return

        resource = "index.html" if path in ("", "/") else path.lstrip("/")
        if "/" in resource and not resource.startswith("assets/"):
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            content = files("garmin_health_insights.web").joinpath(*resource.split("/")).read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(resource)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # noqa: N802 - stdlib method name
        if urlparse(self.path).path != "/api/report":
            self._send_json({"error": "Unknown API endpoint."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json_body()
            report_payload = build_report_payload(payload)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json(report_payload)

    def log_message(self, format: str, *args: object) -> None:
        """Keep local server logs compact."""

        print(f"{self.address_string()} - {format % args}")

    def _read_json_body(self) -> Any:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("Request body is empty.")
        if length > MAX_REQUEST_BYTES:
            raise ValueError("Request body is too large.")

        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def _extract_request_parts(payload: Any) -> tuple[list[dict[str, Any]], date | None, int]:
    if isinstance(payload, list):
        return [_ensure_record(record) for record in payload], None, 21

    if not isinstance(payload, dict):
        raise ValueError("Payload must be a list of records or an object.")

    baseline_days = int(payload.get("baseline_days") or payload.get("baselineDays") or 21)
    target_day = date.fromisoformat(payload["date"]) if payload.get("date") else None

    for key in ("records", "days", "data", "dailyMetrics"):
        value = payload.get(key)
        if isinstance(value, list):
            return [_ensure_record(record) for record in value], target_day, baseline_days

    if all(isinstance(value, dict) for value in payload.values()):
        records: list[dict[str, Any]] = []
        for day, value in payload.items():
            record = dict(value)
            record.setdefault("date", day)
            records.append(record)
        return records, target_day, baseline_days

    raise ValueError("Payload must contain records, days, data or dailyMetrics.")


def _ensure_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("Each record must be an object.")
    return dict(record)


def _report_to_payload(report: InsightReport) -> dict[str, Any]:
    payload = asdict(report)
    payload["day"] = report.day.isoformat()
    return payload

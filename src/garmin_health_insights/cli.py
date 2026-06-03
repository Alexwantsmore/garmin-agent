"""Command line interface for Garmin Health Insights."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from getpass import getpass
from pathlib import Path
from typing import Sequence

from garmin_health_insights.analyzer import HealthAnalyzer
from garmin_health_insights.renderers import render_json, render_markdown
from garmin_health_insights.server import run_server
from garmin_health_insights.sources import GarminConnectSource, GarminExportSource


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="garmin-health-insights",
        description="Generate daily health and training readiness insights from Garmin exports.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Generate a daily readiness report.")
    report.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to a Garmin Connect export or prepared daily metrics file (.json or .csv).",
    )
    report.add_argument(
        "--date",
        help="Target date in YYYY-MM-DD format. Defaults to the newest day in the input.",
    )
    report.add_argument(
        "--baseline-days",
        type=int,
        default=21,
        help="Number of previous days used as personal baseline. Default: 21.",
    )
    report.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Default: markdown.",
    )
    report.add_argument(
        "--output",
        "-o",
        help="Optional path where the report should be written. Prints to stdout when omitted.",
    )

    sync = subparsers.add_parser("sync", help="Download daily metrics from a Garmin Connect account.")
    sync.add_argument("--email", default=os.getenv("GARMIN_EMAIL"), help="Garmin Connect email. Defaults to GARMIN_EMAIL.")
    sync.add_argument(
        "--password-env",
        default="GARMIN_PASSWORD",
        help="Environment variable containing the Garmin Connect password. Default: GARMIN_PASSWORD.",
    )
    sync.add_argument(
        "--tokenstore",
        default=os.getenv("GARMINTOKENS", "~/.garminconnect"),
        help="Directory for Garmin Connect session tokens. Default: ~/.garminconnect.",
    )
    sync.add_argument("--days", type=int, default=30, help="Number of days to download. Default: 30.")
    sync.add_argument("--end-date", help="Last date to download in YYYY-MM-DD format. Default: today.")
    sync.add_argument(
        "--output",
        "-o",
        default="data/garmin_daily.json",
        help="Output JSON file for the web UI or report command. Default: data/garmin_daily.json.",
    )
    sync.add_argument("--include-raw", action="store_true", help="Include raw Garmin endpoint payloads in the output file.")

    serve = subparsers.add_parser("serve", help="Run the local web UI.")
    serve.add_argument("--host", default="127.0.0.1", help="Host to bind. Default: 127.0.0.1.")
    serve.add_argument("--port", type=int, default=8000, help="Port to bind. Default: 8000.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "report":
            return _report(args)
        if args.command == "sync":
            return _sync(args)
        if args.command == "serve":
            return _serve(args)
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    parser.error("Unknown command")
    return 2


def _report(args: argparse.Namespace) -> int:
    target_day = date.fromisoformat(args.date) if args.date else None
    metrics = GarminExportSource(args.input).load()
    report = HealthAnalyzer(baseline_days=args.baseline_days).analyze(metrics, target_day=target_day)

    rendered = render_json(report) if args.format == "json" else render_markdown(report)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


def _sync(args: argparse.Namespace) -> int:
    end_day = date.fromisoformat(args.end_date) if args.end_date else date.today()
    password = os.getenv(args.password_env) if args.password_env else None
    source = GarminConnectSource(
        email=args.email,
        password=password,
        tokenstore=args.tokenstore,
        days=args.days,
        end_day=end_day,
        password_provider=lambda: getpass("Garmin Connect password: "),
        mfa_provider=lambda: input("Garmin MFA code: ").strip(),
    )
    metrics = source.load()
    payload = {
        "source": "garmin_connect",
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "records": [_metric_to_record(metric, include_raw=args.include_raw) for metric in metrics],
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.output == "-":
        print(rendered, end="")
    else:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"Saved {len(metrics)} Garmin Connect days to {output}")
    return 0


def _metric_to_record(metric, *, include_raw: bool) -> dict[str, object]:
    fields = (
        "resting_hr",
        "hrv_ms",
        "sleep_score",
        "sleep_hours",
        "body_battery",
        "stress_score",
        "spo2",
        "steps",
        "calories",
        "training_load",
        "training_readiness",
        "recovery_hours",
        "vo2max",
        "notes",
    )
    record: dict[str, object] = {"date": metric.day.isoformat()}
    for field in fields:
        value = getattr(metric, field)
        if value is not None:
            record[field] = value
    if include_raw:
        record["raw"] = dict(metric.raw)
    return record


def _serve(args: argparse.Namespace) -> int:
    run_server(host=args.host, port=args.port)
    return 0

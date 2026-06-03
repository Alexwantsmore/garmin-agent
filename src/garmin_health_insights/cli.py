"""Command line interface for Garmin Health Insights."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

from garmin_health_insights.analyzer import HealthAnalyzer
from garmin_health_insights.renderers import render_json, render_markdown
from garmin_health_insights.server import run_server
from garmin_health_insights.sources import GarminExportSource


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


def _serve(args: argparse.Namespace) -> int:
    run_server(host=args.host, port=args.port)
    return 0

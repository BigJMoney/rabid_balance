from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


SPARK_PREFIX = "[\u26a1]"
LOG_LINE_RE = re.compile(r"^\[(?P<timestamp>[^\]]+)\] \[[^\]]+\] \[[^\]]+\]: (?P<message>.*)$")
PERF_EVENT_RE = re.compile(r"^\[(?P<actor>[^\]]+)\] (?P<action>BEGIN Perf Test|END Perf Test|Capture Now)$")
MESSAGE_PREFIXES = ("[System] [CHAT] ", "[Not Secure] ")
TPS_WINDOWS = ("5s", "10s", "1m", "5m", "15m")
MSPT_WINDOWS = ("10s", "1m")
MSPT_STATS = ("min", "median", "p95", "max")
CPU_WINDOWS = ("10s", "1m", "15m")
DUPLICATE_EVENT_WINDOW_SECONDS = 1.0


@dataclass
class PerfSession:
    session_index: int
    actor: str | None
    start_timestamp: datetime | None
    capture_count: int = 0


@dataclass
class CaptureRecord:
    session_index: int
    session_actor: str | None
    session_start_timestamp: datetime | None
    capture_index: int
    capture_actor: str | None
    capture_timestamp: datetime | None
    spark_timestamp: datetime | None = None
    tps_values: dict[str, float] = field(default_factory=dict)
    tps_starred: dict[str, bool] = field(default_factory=dict)
    mspt_values: dict[str, float] = field(default_factory=dict)
    cpu_values: dict[str, int] = field(default_factory=dict)

    def has_any_metric(self) -> bool:
        return bool(self.tps_values or self.mspt_values or self.cpu_values)

    def note_spark_timestamp(self, timestamp: datetime) -> None:
        if self.spark_timestamp is None:
            self.spark_timestamp = timestamp

    def to_row(self, source_log: str, parsed_at: str) -> dict[str, str | int | float]:
        row: dict[str, str | int | float] = {
            "source_log": source_log,
            "parsed_at": parsed_at,
            "session_index": self.session_index,
            "session_actor": self.session_actor or "",
            "session_start_timestamp": format_timestamp(self.session_start_timestamp),
            "capture_index": self.capture_index,
            "capture_actor": self.capture_actor or "",
            "capture_timestamp": format_timestamp(self.capture_timestamp),
            "spark_timestamp": format_timestamp(self.spark_timestamp),
            "seconds_since_session_start": "",
            "seconds_from_capture_to_spark": "",
        }

        if self.session_start_timestamp is not None and self.capture_timestamp is not None:
            row["seconds_since_session_start"] = round(
                (self.capture_timestamp - self.session_start_timestamp).total_seconds(),
                3,
            )
        if self.capture_timestamp is not None and self.spark_timestamp is not None:
            row["seconds_from_capture_to_spark"] = round(
                (self.spark_timestamp - self.capture_timestamp).total_seconds(),
                3,
            )

        for window in TPS_WINDOWS:
            row[f"tps_{window}"] = self.tps_values.get(window, "")
            row[f"tps_{window}_starred"] = (
                str(self.tps_starred.get(window, False)).lower() if window in self.tps_starred else ""
            )

        for window in MSPT_WINDOWS:
            for stat in MSPT_STATS:
                row[f"mspt_{window}_{stat}"] = self.mspt_values.get(f"{window}_{stat}", "")

        for scope in ("system", "process"):
            for window in CPU_WINDOWS:
                row[f"cpu_{scope}_{window}_pct"] = self.cpu_values.get(f"{scope}_{window}", "")

        return row


@dataclass(frozen=True)
class PerfEvent:
    actor: str
    action: str
    timestamp: datetime


def format_timestamp(value: datetime | None) -> str:
    return value.isoformat(timespec="milliseconds") if value is not None else ""


def parse_log_timestamp(raw_timestamp: str) -> datetime:
    return datetime.strptime(raw_timestamp, "%d%b%Y %H:%M:%S.%f")


def normalize_message(message: str) -> str:
    normalized = message.strip()
    changed = True
    while changed:
        changed = False
        for prefix in MESSAGE_PREFIXES:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                changed = True
    return normalized


def parse_log_line(line: str) -> tuple[datetime, str] | None:
    match = LOG_LINE_RE.match(line.rstrip("\n"))
    if match is None:
        return None
    timestamp = parse_log_timestamp(match.group("timestamp"))
    message = normalize_message(match.group("message"))
    return timestamp, message


def parse_perf_event(message: str, timestamp: datetime) -> PerfEvent | None:
    match = PERF_EVENT_RE.match(message)
    if match is None:
        return None
    return PerfEvent(actor=match.group("actor"), action=match.group("action"), timestamp=timestamp)


def is_duplicate_event(previous: PerfEvent | None, current: PerfEvent) -> bool:
    if previous is None:
        return False
    if previous.actor != current.actor or previous.action != current.action:
        return False
    return (current.timestamp - previous.timestamp).total_seconds() <= DUPLICATE_EVENT_WINDOW_SECONDS


def parse_tps_values(text: str) -> tuple[dict[str, float], dict[str, bool]]:
    tokens = [token.strip() for token in text.split(",")]
    if len(tokens) != len(TPS_WINDOWS):
        raise ValueError(f"Expected {len(TPS_WINDOWS)} TPS values, found {len(tokens)} in: {text}")

    values: dict[str, float] = {}
    starred: dict[str, bool] = {}
    for window, token in zip(TPS_WINDOWS, tokens, strict=True):
        starred[window] = token.startswith("*")
        values[window] = float(token.lstrip("*"))
    return values, starred


def parse_tick_values(text: str) -> dict[str, float]:
    groups = [group.strip() for group in text.split(";") if group.strip()]
    if len(groups) != len(MSPT_WINDOWS):
        raise ValueError(f"Expected {len(MSPT_WINDOWS)} MSPT groups, found {len(groups)} in: {text}")

    values: dict[str, float] = {}
    for window, group in zip(MSPT_WINDOWS, groups, strict=True):
        stats = [token.strip() for token in group.split("/")]
        if len(stats) != len(MSPT_STATS):
            raise ValueError(f"Expected {len(MSPT_STATS)} MSPT stats, found {len(stats)} in: {group}")
        for stat_name, stat_value in zip(MSPT_STATS, stats, strict=True):
            values[f"{window}_{stat_name}"] = float(stat_value)
    return values


def parse_cpu_values(text: str) -> tuple[str, dict[str, int]]:
    numeric_text, _, suffix = text.partition("(")
    scope = suffix.rstrip(")").strip()
    if scope not in {"system", "process"}:
        raise ValueError(f"Expected CPU scope to be system or process, found: {text}")

    tokens = [token.strip() for token in numeric_text.split(",") if token.strip()]
    if len(tokens) != len(CPU_WINDOWS):
        raise ValueError(f"Expected {len(CPU_WINDOWS)} CPU values, found {len(tokens)} in: {text}")

    values: dict[str, int] = {}
    for window, token in zip(CPU_WINDOWS, tokens, strict=True):
        values[f"{scope}_{window}"] = int(token.rstrip("%"))
    return scope, values


def start_capture(session: PerfSession | None, timestamp: datetime, actor: str | None, completed_count: int) -> CaptureRecord:
    if session is not None:
        session.capture_count += 1
        capture_index = session.capture_count
        session_index = session.session_index
        session_actor = session.actor
        session_start_timestamp = session.start_timestamp
    else:
        capture_index = completed_count + 1
        session_index = 0
        session_actor = None
        session_start_timestamp = None

    return CaptureRecord(
        session_index=session_index,
        session_actor=session_actor,
        session_start_timestamp=session_start_timestamp,
        capture_index=capture_index,
        capture_actor=actor,
        capture_timestamp=timestamp,
    )


def parse_spark_log(log_path: Path) -> list[CaptureRecord]:
    captures: list[CaptureRecord] = []
    current_session: PerfSession | None = None
    current_capture: CaptureRecord | None = None
    expected_value_kind: str | None = None
    last_event: PerfEvent | None = None
    session_counter = 0

    with log_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            parsed_line = parse_log_line(line)
            if parsed_line is None:
                continue

            timestamp, message = parsed_line
            perf_event = parse_perf_event(message, timestamp)
            if perf_event is not None:
                if is_duplicate_event(last_event, perf_event):
                    continue
                last_event = perf_event

                if perf_event.action == "BEGIN Perf Test":
                    if current_capture is not None and current_capture.has_any_metric():
                        captures.append(current_capture)
                    session_counter += 1
                    current_session = PerfSession(
                        session_index=session_counter,
                        actor=perf_event.actor,
                        start_timestamp=perf_event.timestamp,
                    )
                    current_capture = None
                    expected_value_kind = None
                    continue

                if perf_event.action == "END Perf Test":
                    if current_capture is not None and current_capture.has_any_metric():
                        captures.append(current_capture)
                    current_capture = None
                    current_session = None
                    expected_value_kind = None
                    continue

                if perf_event.action == "Capture Now":
                    if current_capture is not None and current_capture.has_any_metric():
                        captures.append(current_capture)
                        current_capture = None
                    if current_capture is None:
                        current_capture = start_capture(
                            session=current_session,
                            timestamp=perf_event.timestamp,
                            actor=perf_event.actor,
                            completed_count=len(captures),
                        )
                    expected_value_kind = None
                    continue

            if not message.startswith(SPARK_PREFIX):
                continue

            spark_body = message[len(SPARK_PREFIX):].strip()
            if current_capture is None:
                current_capture = start_capture(
                    session=current_session,
                    timestamp=timestamp,
                    actor=None,
                    completed_count=len(captures),
                )
            if spark_body:
                current_capture.note_spark_timestamp(timestamp)

            if not spark_body:
                continue

            if spark_body.startswith("TPS from last "):
                expected_value_kind = "tps"
                continue
            if spark_body.startswith("Tick durations "):
                expected_value_kind = "tick"
                continue
            if spark_body.startswith("CPU usage from last "):
                expected_value_kind = "cpu_system"
                continue

            try:
                if expected_value_kind == "tps":
                    values, starred = parse_tps_values(spark_body)
                    current_capture.tps_values.update(values)
                    current_capture.tps_starred.update(starred)
                    expected_value_kind = None
                    continue

                if expected_value_kind == "tick":
                    current_capture.mspt_values.update(parse_tick_values(spark_body))
                    expected_value_kind = None
                    continue

                if expected_value_kind in {"cpu_system", "cpu_process"}:
                    scope, values = parse_cpu_values(spark_body)
                    current_capture.cpu_values.update(values)
                    expected_value_kind = "cpu_process" if scope == "system" else None
                    continue
            except ValueError as exc:
                raise ValueError(f"Line {line_number}: {exc}") from exc

    if current_capture is not None and current_capture.has_any_metric():
        captures.append(current_capture)

    return captures


def build_fieldnames() -> list[str]:
    fieldnames = [
        "source_log",
        "session_start_timestamp",
        "session_index",
        "capture_index",
        "mspt_10s_min",
        "mspt_10s_median",
        "mspt_10s_p95",
        "mspt_10s_max",
        "capture_timestamp",
        "mspt_1m_min",
        "mspt_1m_median",
        "mspt_1m_p95",
        "mspt_1m_max",
        "parsed_at",
        "session_actor",
        "capture_actor",
        "spark_timestamp",
        "seconds_since_session_start",
        "seconds_from_capture_to_spark",
    ]
    for window in TPS_WINDOWS:
        fieldnames.append(f"tps_{window}")
        fieldnames.append(f"tps_{window}_starred")
    for scope in ("system", "process"):
        for window in CPU_WINDOWS:
            fieldnames.append(f"cpu_{scope}_{window}_pct")
    return fieldnames


def write_capture_csv(rows: list[dict[str, str | int | float]], output_path: Path) -> None:
    fieldnames = build_fieldnames()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def collect_log_paths(input_path: Path, recursive: bool = False) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".log":
            raise ValueError(f"Input file must have a .log extension: {input_path}")
        return [input_path]

    if input_path.is_dir():
        iterator = input_path.rglob("*.log") if recursive else input_path.glob("*.log")
        return sorted(path for path in iterator if path.is_file())

    raise FileNotFoundError(f"Input path does not exist: {input_path}")


def default_output_path(input_path: Path) -> Path:
    return (input_path if input_path.is_dir() else input_path.parent) / "spark_perf_captures.csv"


def collate_spark_log(input_path: Path, output_path: Path | None = None, recursive: bool = False) -> dict[str, object]:
    if output_path is None:
        output_path = default_output_path(input_path)

    log_paths = collect_log_paths(input_path, recursive=recursive)
    parsed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    rows: list[dict[str, str | int | float]] = []
    for log_path in log_paths:
        captures = parse_spark_log(log_path)
        for capture in captures:
            rows.append(capture.to_row(source_log=log_path.name, parsed_at=parsed_at))

    write_capture_csv(rows, output_path)

    return {
        "input_path": input_path,
        "output_path": output_path,
        "rows_written": len(rows),
        "log_count": len(log_paths),
        "parsed_at": parsed_at,
        "recursive": recursive,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collate Spark MSPT/TPS chat captures from a Minecraft .log file or folder into a CSV.",
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a Spark-containing .log file or to a folder that should be scanned for .log files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        type=Path,
        help="Optional CSV output path. Defaults to spark_perf_captures.csv in the input folder.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="When the input is a folder, include .log files from subdirectories recursively.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    result = collate_spark_log(args.input_path, args.output_path, recursive=args.recursive)
    print(f"Wrote {result['rows_written']} rows from {result['log_count']} log files to {result['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

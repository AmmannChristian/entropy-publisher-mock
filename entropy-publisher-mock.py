#!/usr/bin/env python3
"""Publish mock TDC timestamps to MQTT for exercising entropy-tdc-gateway."""

from __future__ import annotations

import argparse
import random
import signal
import sys
import threading
from dataclasses import dataclass
from typing import Iterable, List

try:  # pragma: no cover - thin wrapper
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover - optional dependency
    mqtt = None  # type: ignore[assignment]


@dataclass
class TimestampGenerator:
    """Generate mock timestamps that emulate 24-bit TDC counter behavior.

    The fine counter advances in picoseconds and wraps at ``max_fine``. Each
    fine-counter rollover increments the coarse counter, which wraps at
    ``max_coarse`` to mirror hardware rollover semantics.
    """

    coarse: int = 0
    fine: int = 0
    increment_ps: int = 1000
    jitter_ps: int = 0
    max_fine: int = 100_000
    max_coarse: int = 16_777_215  # Maximum value representable by a 24-bit counter.

    def next(self) -> int:
        """Return the next timestamp value with configured increment and jitter."""
        jitter = random.randint(-self.jitter_ps, self.jitter_ps) if self.jitter_ps else 0
        increment = max(self.increment_ps + jitter, 1)

        self.fine += increment

        # Handle fine counter overflow
        while self.fine >= self.max_fine:
            self.fine -= self.max_fine
            self.coarse += 1

            # Handle coarse counter overflow (24-bit wraparound)
            if self.coarse > self.max_coarse:
                self.coarse = 0

        return self.fine + self.coarse * self.max_fine


def parse_channels(raw: str) -> List[int]:
    """Parse comma-separated channels and inclusive ranges into channel IDs.

    The expected syntax is a comma-separated list of integers or ranges in the
    form ``start-end``. For example, ``1,2,5-8`` expands to
    ``[1, 2, 5, 6, 7, 8]``.
    """
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("at least one channel must be provided")
    channels: List[int] = []
    for part in parts:
        if "-" in part:
            start, end = part.split("-", 1)
            channels.extend(range(int(start), int(end) + 1))
        else:
            channels.append(int(part))
    return channels


def build_arg_parser() -> argparse.ArgumentParser:
    """Build and return the command-line interface specification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="MQTT broker host (default: %(default)s)")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port (default: %(default)s)")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--client-id", default="mock-tdc-publisher", help="MQTT client identifier")
    parser.add_argument(
        "--topic",
        default="timestamps/channel/{channel}",
        help="Topic template. Use {channel} placeholder (default: %(default)s)",
    )
    parser.add_argument(
        "--channels",
        type=parse_channels,
        default=[1],
        help="Comma separated list or ranges (e.g. '1,2,5-8'). Default: 1",
    )
    parser.add_argument("--qos", type=int, choices=(0, 1), default=0, help="MQTT QoS")
    parser.add_argument("--retain", action="store_true", help="Publish with retain flag")
    parser.add_argument(
        "--rate",
        type=float,
        default=20.0,
        help="Events per channel per second (default: %(default)s)",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=0,
        help="Stop after publishing this many events (0 = run forever)",
    )
    parser.add_argument(
        "--base-timestamp-ps",
        type=int,
        default=None,
        help="Starting timestamp in picoseconds (default: current time).",
    )
    parser.add_argument(
        "--increment-ps",
        type=int,
        default=1_000,
        help="Nominal increment per event in picoseconds",
    )
    parser.add_argument(
        "--jitter-ps",
        type=int,
        default=0,
        help="Random jitter applied to increment (uniform ± value)",
    )
    parser.add_argument(
        "--tls-ca",
        help="Path to CA file for TLS. Enables TLS when provided",
    )
    parser.add_argument("--insecure", action="store_true", help="Skip TLS certificate verification")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without contacting MQTT")
    return parser


def connect_client(args: argparse.Namespace) -> mqtt.Client | None:
    """Create and connect an MQTT client according to runtime arguments.

    Returns ``None`` when dry-run mode is enabled. Terminates the process when
    MQTT support is required but unavailable.
    """
    if args.dry_run:
        return None
    if mqtt is None:
        print(
            "paho-mqtt is required. Install with `python3 -m pip install paho-mqtt`.",
            file=sys.stderr,
        )
        sys.exit(1)

    client_kwargs = {
        "client_id": args.client_id,
        "clean_session": True,
        "protocol": mqtt.MQTTv311,
    }
    # Use the new callback API to avoid deprecation warnings when available.
    if hasattr(mqtt, "CallbackAPIVersion"):
        client_kwargs["callback_api_version"] = mqtt.CallbackAPIVersion.VERSION2

    client = mqtt.Client(**client_kwargs)
    if args.username:
        client.username_pw_set(args.username, args.password)
    if args.tls_ca:
        client.tls_set(ca_certs=args.tls_ca)
        if args.insecure:
            client.tls_insecure_set(True)
    client.connect(args.host, args.port, keepalive=30)
    client.loop_start()
    return client


def publish_loop(args: argparse.Namespace) -> None:
    """Publish generated timestamps for each configured channel until stopped.

    The loop exits on operating-system termination signals or after
    ``--max-events`` has been reached.
    """
    stop = threading.Event()

    def _handle_signal(signum, _frame):  # pragma: no cover - signal wiring
        print(f"Received signal {signum}, shutting down...")
        stop.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    client = connect_client(args)

    # Initialize with realistic 24-bit TDC values (not Unix timestamp)
    generator = TimestampGenerator(
        coarse=0,
        fine=0,
        increment_ps=args.increment_ps,
        jitter_ps=args.jitter_ps
    )

    total_events = 0
    per_channel_delay = 0.0 if args.rate <= 0 else 1.0 / args.rate
    print(
        f"Publishing to {args.host}:{args.port} -> topic '{args.topic}' on channels {args.channels}"
    )

    while not stop.is_set():
        for channel in args.channels:
            timestamp = generator.next()
            topic = args.topic.format(channel=channel)
            payload = str(timestamp)

            if args.dry_run:
                print(f"[DRY-RUN] {topic}: {payload}")
            else:
                result = client.publish(topic, payload, qos=args.qos, retain=args.retain)
                result.wait_for_publish()
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    print(f"Failed to publish to {topic}: {mqtt.error_string(result.rc)}", file=sys.stderr)

            total_events += 1
            if args.max_events and total_events >= args.max_events:
                stop.set()
                break

            if stop.wait(per_channel_delay):
                break

        if args.max_events and total_events >= args.max_events:
            break

    if client is not None:
        client.loop_stop()
        client.disconnect()
    print(f"Sent {total_events} events")


if __name__ == "__main__":
    publish_loop(build_arg_parser().parse_args())

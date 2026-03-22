"""Shared fixtures for entropy-publisher-mock tests."""

import argparse
import importlib
import sys

import pytest


@pytest.fixture()
def mock_module():
    """Import the main module (hyphenated filename needs importlib).

    The module must be registered in sys.modules before exec_module so that
    ``from __future__ import annotations`` + dataclass field resolution can
    look up the module by name.
    """
    mod_name = "entropy_publisher_mock"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(
        mod_name,
        "entropy-publisher-mock.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def dry_run_args():
    """Return a minimal argparse.Namespace for dry-run mode."""
    return argparse.Namespace(
        host="127.0.0.1",
        port=1883,
        username=None,
        password=None,
        client_id="test-client",
        topic="timestamps/channel/{channel}",
        channels=[1],
        qos=0,
        retain=False,
        rate=0,
        max_events=4,
        base_timestamp_ps=None,
        increment_ps=1000,
        jitter_ps=0,
        tls_ca=None,
        insecure=False,
        dry_run=True,
    )

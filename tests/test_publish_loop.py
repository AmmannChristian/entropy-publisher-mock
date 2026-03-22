"""Tests for connect_client, build_arg_parser, and publish_loop."""

import sys
from unittest.mock import patch

import pytest


def test_connect_client_returns_none_in_dry_run(mock_module, dry_run_args):
    result = mock_module.connect_client(dry_run_args)
    assert result is None


def test_connect_client_exits_when_mqtt_missing(mock_module, dry_run_args):
    dry_run_args.dry_run = False
    with patch.object(mock_module, "mqtt", None):
        with pytest.raises(SystemExit) as exc_info:
            mock_module.connect_client(dry_run_args)
        assert exc_info.value.code == 1


def test_build_arg_parser_defaults(mock_module):
    parser = mock_module.build_arg_parser()
    args = parser.parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 1883
    assert args.rate == 20.0
    assert args.max_events == 0
    assert args.dry_run is False
    assert args.qos == 0
    assert args.increment_ps == 1000
    assert args.jitter_ps == 0


def test_build_arg_parser_channels(mock_module):
    parser = mock_module.build_arg_parser()
    args = parser.parse_args(["--channels", "1,3-5"])
    assert args.channels == [1, 3, 4, 5]


def test_publish_loop_dry_run_respects_max_events(mock_module, dry_run_args, capsys):
    dry_run_args.max_events = 3
    dry_run_args.channels = [1]
    mock_module.publish_loop(dry_run_args)
    captured = capsys.readouterr()
    assert "Sent 3 events" in captured.out
    assert captured.out.count("[DRY-RUN]") == 3


def test_publish_loop_dry_run_multiple_channels(mock_module, dry_run_args, capsys):
    dry_run_args.max_events = 4
    dry_run_args.channels = [1, 2]
    mock_module.publish_loop(dry_run_args)
    captured = capsys.readouterr()
    assert "Sent 4 events" in captured.out
    assert "channel/1" in captured.out
    assert "channel/2" in captured.out

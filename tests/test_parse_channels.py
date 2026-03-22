"""Tests for parse_channels."""

import argparse

import pytest


def test_single_channel(mock_module):
    assert mock_module.parse_channels("1") == [1]


def test_multiple_channels(mock_module):
    assert mock_module.parse_channels("1,2,3") == [1, 2, 3]


def test_range(mock_module):
    assert mock_module.parse_channels("5-8") == [5, 6, 7, 8]


def test_mixed(mock_module):
    assert mock_module.parse_channels("1,2,5-8") == [1, 2, 5, 6, 7, 8]


def test_whitespace_handling(mock_module):
    assert mock_module.parse_channels(" 1 , 2 , 3 ") == [1, 2, 3]


def test_empty_string_raises(mock_module):
    with pytest.raises(argparse.ArgumentTypeError, match="at least one channel"):
        mock_module.parse_channels("")


def test_only_whitespace_raises(mock_module):
    with pytest.raises(argparse.ArgumentTypeError, match="at least one channel"):
        mock_module.parse_channels("   ")


def test_single_element_range(mock_module):
    assert mock_module.parse_channels("5-5") == [5]

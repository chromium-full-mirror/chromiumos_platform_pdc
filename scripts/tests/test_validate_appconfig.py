# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error,protected-access

"""Unit tests for presubmit_checks/validate_appconfig.py"""

import pathlib

from presubmit_checks.validate_appconfig import AppConfigValidator
from presubmit_checks.validate_appconfig import InvalidVersion
from presubmit_checks.validate_appconfig import parse_appconfig
from presubmit_checks.validate_appconfig import Version
import pytest


def test_version_parsing():
    v = Version("2.34")
    assert v.components == (2, 34)
    assert str(v) == "2.34"


def test_version_comparison():
    v1 = Version("2.26")
    v2 = Version("2.34")
    v3 = Version("2.34.1")

    assert v1 < v2
    assert v2 < v3
    assert v2 == Version("2.34")
    assert v3 >= v2


def test_invalid_version():
    with pytest.raises(InvalidVersion):
        Version("2.34.a")


def test_parse_appconfig():
    data = {
        "metadata": {
            "toolBuildVersion": "2.37",
            "mode": "test",
            "cpu": "arm",
            "timeStamp": "12345",
        }
    }
    config = parse_appconfig(pathlib.Path("test.json"), data)
    assert config is not None
    assert config.tool_build_version_str == "2.37"


def test_parse_appconfig_invalid_version_logs_error():
    validator = AppConfigValidator()
    data = {
        "metadata": {
            "toolBuildVersion": "2.34.invalid",
            "mode": "test",
            "cpu": "arm",
            "timeStamp": "12345",
        }
    }
    config = parse_appconfig(pathlib.Path("test.json"), data)
    assert config is not None
    assert config.tool_build_version_str == "2.34.invalid"

    validator.validate(config, None)
    assert len(validator.errors) == 1
    assert "Invalid toolBuildVersion format" in validator.errors[0]


def test_validate_version_decreased():
    validator = AppConfigValidator()

    curr_data = {"metadata": {"toolBuildVersion": "2.26"}}
    base_data = {"metadata": {"toolBuildVersion": "2.37"}}

    curr_cfg = parse_appconfig(pathlib.Path("test.json"), curr_data)
    base_cfg = parse_appconfig(pathlib.Path("test.json"), base_data)

    validator._validate_version_not_decreased(curr_cfg, base_cfg)
    assert len(validator.errors) > 0

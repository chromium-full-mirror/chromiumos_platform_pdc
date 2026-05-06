#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Validates that appconfig.json files follow project requirements.

This script checks for:
- Valid JSON format.
- Presence of metadata.toolBuildVersion and other required metadata.
- toolBuildVersion is not decreased compared to the base commit.
"""

import dataclasses
import json
import logging
import os
import pathlib
import subprocess
import sys
from typing import Any, Dict, List, Optional

from packaging import version


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


@dataclasses.dataclass
class TIAppConfig:
    """Represents a parsed TI appconfig.json file."""

    path: pathlib.Path
    data: Dict[str, Any]
    tool_build_version: Optional[version.Version] = None


class AppConfigValidator:
    """Validator for appconfig.json files."""

    def __init__(self):
        self.errors: List[str] = []
        self.required_metadata = [
            "toolBuildVersion",
            "mode",
            "cpu",
            "timeStamp",
        ]

    def log_error(self, message: str):
        """Logs an error message and tracks it."""
        logger.error(message)
        self.errors.append(message)

    def is_appconfig(self, data: Dict[str, Any]) -> bool:
        """Determines if the JSON data represents a TI appconfig."""
        if not data:
            return False
        return "metadata" in data

    def validate(self, current: TIAppConfig, base: Optional[TIAppConfig]):
        self._validate_metadata(current)
        self._validate_version_not_decreased(current, base)
        # New validators can be added here

    def _validate_metadata(self, config: TIAppConfig):
        """Validates metadata fields."""
        metadata = config.data.get("metadata")

        for field in self.required_metadata:
            if field not in metadata:
                self.log_error(f"{config.path}: metadata is missing '{field}'")

    def _validate_version_not_decreased(
        self, current: TIAppConfig, base: Optional[TIAppConfig]
    ):
        """Checks if the version has decreased compared to base."""
        if not current.tool_build_version:
            self.log_error(
                f"{current.path}: missing or invalid toolBuildVersion"
            )
            return

        if not base or not base.tool_build_version:
            return

        if current.tool_build_version < base.tool_build_version:
            msg = (
                f"{current.path}: toolBuildVersion "
                f"'{current.tool_build_version}' is lower than the "
                f"previous version '{base.tool_build_version}'."
            )
            self.log_error(msg)


def get_git_file_content(commit: str, file_path: pathlib.Path) -> Optional[str]:
    """Gets the content of the file from a specific git commit."""
    try:
        cmd = ["git", "show", f"{commit}:{file_path.as_posix()}"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception as e:
        logger.warning(
            "Exception during git show for %s at %s: %s", file_path, commit, e
        )
        return None


def parse_appconfig(path: pathlib.Path, data) -> Optional[TIAppConfig]:
    """Parses a JSON string into an AppConfig object."""

    version_str = data.get("metadata", {}).get("toolBuildVersion")
    v = None
    if version_str:
        try:
            v = version.parse(version_str)
        except version.InvalidVersion:
            logger.warning(
                "%s: Invalid toolBuildVersion format: '%s'",
                path,
                version_str,
            )

    return TIAppConfig(path=path, data=data, tool_build_version=v)


def parse_appconfig_changes(path, data, base_data):
    current_config = parse_appconfig(path, data)
    base_config = parse_appconfig(path, base_data) if base_data else None
    return current_config, base_config


def examinate_json_file(
    path: pathlib.Path, commit: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Reads and parses a JSON file from git or disk."""
    if commit is None:
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.warning("Error reading %s from disk: %s", path, e)
            return None

    current_content = get_git_file_content(commit, path)
    if not current_content:
        return None
    try:
        return json.loads(current_content)
    except json.JSONDecodeError as e:
        logger.warning("Error parsing %s from commit %s: %s", path, commit, e)
        return None


def main(argv: List[str], presubmit_commit: Optional[str]) -> int:
    """Main entry point."""
    validator = AppConfigValidator()

    for arg in argv:
        path = pathlib.Path(arg)
        if path.suffix.lower() != ".json":
            continue

        if presubmit_commit:
            json_current_data = examinate_json_file(path, presubmit_commit)
            json_base_data = examinate_json_file(path, f"{presubmit_commit}~1")
            source_desc = f"commit {presubmit_commit}"
        else:
            # Local mode: disk vs HEAD
            json_current_data = examinate_json_file(path, None)
            json_base_data = examinate_json_file(path, "HEAD")
            source_desc = "disk"

        if not validator.is_appconfig(json_current_data):
            continue

        # Parse new and old file to TIAppConfig
        current_config, base_config = parse_appconfig_changes(
            path, json_current_data, json_base_data
        )
        if not current_config:
            validator.log_error(f"Failed to parse {path} from {source_desc}")
            continue

        validator.validate(current_config, base_config)

    if validator.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ.get("PRESUBMIT_COMMIT")))

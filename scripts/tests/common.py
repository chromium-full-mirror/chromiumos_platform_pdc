# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common utilities for test code"""

from pathlib import Path


def get_test_file_path(filename: Path | str) -> Path:
    """Return an absolute path to the given file in the test_files/ dir"""
    return Path(__file__).parent.resolve() / "test_files" / filename

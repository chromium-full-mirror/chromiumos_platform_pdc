#!/usr/bin/env vpython3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script for checking RTK FW images"""

# pylint: disable=import-error
from pdclib import common


if __name__ == "__main__":
    common.add_pdclib_private()

    import pdclib_private.rtk_verify_fw

    pdclib_private.rtk_verify_fw.cli_app()

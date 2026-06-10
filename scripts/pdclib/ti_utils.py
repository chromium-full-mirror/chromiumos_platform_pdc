# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities for inspecting TI PDC FW images"""

import binascii
from pathlib import Path
import struct
from typing import Tuple

# pylint: disable=import-modules-only
from pdclib.ti_constants import TiFwFormat
from pdclib.ti_constants import TiFwOffset
from pdclib.ti_constants import TiHeader


def format_ti_config_string(s: bytes) -> str:
    """Get string representation of customer use register bytes"""
    if s.startswith(b"GOOG"):
        # Treat as ASCII (Unified config identifier scheme)
        return s.decode("ascii")
    else:
        # Treat as hex string (legacy integer config ID)
        return f"0x{binascii.hexlify(s).decode('ascii')}"


def read_base_fw_ver_and_proj_name(
    binary_path: Path,
) -> Tuple[int, int, int, str]:
    """Read FW version info from TI binary file."""

    with open(binary_path, "rb") as f:
        data = f.read()
        header = data[0:4]
        if header in (TiHeader.TFU_BUNDLE_TYPE_A, TiHeader.TFU_BUNDLE_TYPE_B):
            # Either a standalone FW image or a FW+appconfig bundle. Start with
            # getting FW version:
            patch, minor, major, _ = struct.unpack(
                TiFwFormat.FWVER,
                data[
                    TiFwOffset.FWVER_OFFSET : TiFwOffset.FWVER_OFFSET
                    + struct.calcsize(TiFwFormat.FWVER)
                ],
            )

            # See if there is an appconfig section after the FW data

            (num_fw_blocks,) = struct.unpack(
                TiFwFormat.NUM_BLOCKS,
                data[
                    TiFwOffset.NUM_BLOCKS_OFFSET : TiFwOffset.NUM_BLOCKS_OFFSET
                    + struct.calcsize(TiFwFormat.NUM_BLOCKS)
                ],
            )
            (fw_size,) = struct.unpack(
                TiFwFormat.FW_SIZE,
                data[
                    TiFwOffset.FW_SIZE_OFFSET : TiFwOffset.FW_SIZE_OFFSET
                    + struct.calcsize(TiFwFormat.FW_SIZE)
                ],
            )
            appconfig_offset = data.find(
                TiHeader.APPCONFIG_SECTION,
                fw_size
                + TiFwOffset.HEADER_BLOCK_LENGTH
                + (TiFwOffset.DATA_METADATA_LENGTH * (num_fw_blocks + 1))
                + TiFwOffset.METADATA_OFFSET,
            )

            if appconfig_offset == -1:
                # No appconfig section found
                return major, minor, patch, None

            # Get project name (customer use register)
            return (
                major,
                minor,
                patch,
                format_ti_config_string(
                    data[
                        appconfig_offset
                        + TiFwOffset.PROJ_NAME_OFFSET : appconfig_offset
                        + TiFwOffset.PROJ_NAME_OFFSET
                        + TiFwOffset.PROJ_NAME_LENGTH
                    ]
                ),
            )

        elif header == TiHeader.APPCONFIG_SECTION:
            # Standalone appconfig file. No FW version available.
            return (
                None,
                None,
                None,
                format_ti_config_string(
                    data[
                        # pylint: disable=line-too-long
                        TiFwOffset.PROJ_NAME_OFFSET : TiFwOffset.PROJ_NAME_OFFSET
                        + TiFwOffset.PROJ_NAME_LENGTH
                    ]
                ),
            )
        else:
            raise RuntimeError(
                "Unknown file header "
                f"{binascii.hexlify(header, '.').decode('ascii')}"
            )

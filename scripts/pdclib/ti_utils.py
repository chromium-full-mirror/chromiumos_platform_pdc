# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities for inspecting TI PDC FW images"""

import binascii
from pathlib import Path
import struct
from typing import Tuple


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

    HEADER_FLASH_SECTION = b"\x03\x00\xef\xac"
    HEADER_APPCONFIG_SECTION = b"\x03\x00\xea\xac"

    FWVER_OFFSET = 0x4F4
    FWVER_FORMAT = "BBBB"

    NUM_BLOCKS_OFFSET = 0x4
    NUM_BLOCKS_FORMAT = "<H"

    FW_SIZE_OFFSET = 0x4F8
    FW_SIZE_FORMAT = "<I"

    PROJ_NAME_OFFSET = 30
    PROJ_NAME_LENGTH = 8

    HEADER_BLOCK_LENGTH = 0x800
    DATA_METADATA_LENGTH = 0x8
    METADATA_OFFSET = 0x4

    with open(binary_path, "rb") as f:
        data = f.read()
        header = data[0:4]
        if header == HEADER_FLASH_SECTION:
            # Either a standalone FW image or a FW+appconfig bundle. Start with
            # getting FW version:
            patch, minor, major, _ = struct.unpack(
                FWVER_FORMAT,
                data[
                    FWVER_OFFSET : FWVER_OFFSET + struct.calcsize(FWVER_FORMAT)
                ],
            )

            # See if there is an appconfig section after the FW data

            (num_fw_blocks,) = struct.unpack(
                NUM_BLOCKS_FORMAT,
                data[
                    NUM_BLOCKS_OFFSET : NUM_BLOCKS_OFFSET
                    + struct.calcsize(NUM_BLOCKS_FORMAT)
                ],
            )
            (fw_size,) = struct.unpack(
                FW_SIZE_FORMAT,
                data[
                    FW_SIZE_OFFSET : FW_SIZE_OFFSET
                    + struct.calcsize(FW_SIZE_FORMAT)
                ],
            )
            appconfig_offset = data.find(
                HEADER_APPCONFIG_SECTION,
                fw_size
                + HEADER_BLOCK_LENGTH
                + (DATA_METADATA_LENGTH * (num_fw_blocks + 1))
                + METADATA_OFFSET,
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
                        + PROJ_NAME_OFFSET : appconfig_offset
                        + PROJ_NAME_OFFSET
                        + PROJ_NAME_LENGTH
                    ]
                ),
            )

        elif header == HEADER_APPCONFIG_SECTION:
            # Standalone appconfig file. No FW version available.
            return (
                None,
                None,
                None,
                format_ti_config_string(
                    data[PROJ_NAME_OFFSET : PROJ_NAME_OFFSET + PROJ_NAME_LENGTH]
                ),
            )
        else:
            raise RuntimeError(
                "Unknown file header "
                f"{binascii.hexlify(header, '.').decode('ascii')}"
            )

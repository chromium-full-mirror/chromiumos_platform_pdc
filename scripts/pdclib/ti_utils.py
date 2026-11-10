# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities for inspecting TI PDC FW images"""

import binascii
from pathlib import Path
import struct

# pylint: disable=import-modules-only
from pdclib.fw_ver import PdcFwSeries
from pdclib.fw_ver import PdcFwVer
from pdclib.fw_ver import PdcVendor
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
) -> PdcFwVer:
    """Read FW version info from TI binary file."""

    with open(binary_path, "rb") as f:
        data = f.read()
        header = data[0:4]
        if header in (TiHeader.TFU_BUNDLE_TYPE_A, TiHeader.TFU_BUNDLE_TYPE_B):
            # Either a standalone FW image or a FW+appconfig bundle. Start with
            # getting FW version:
            patch, minor, major, series = struct.unpack(
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
                project_name = None
            else:
                # Get project name (customer use register)
                project_name = format_ti_config_string(
                    data[
                        appconfig_offset
                        + TiFwOffset.PROJ_NAME_OFFSET : appconfig_offset
                        + TiFwOffset.PROJ_NAME_OFFSET
                        + TiFwOffset.PROJ_NAME_LENGTH
                    ]
                )

            return PdcFwVer(
                vendor=PdcVendor.TI,
                major=major,
                minor=minor,
                patch=patch,
                project_name=project_name,
                series={
                    # Type-A images
                    0x00: PdcFwSeries.TI_PRODUCTION,
                    0xC0: PdcFwSeries.TI_RELEASE_CANDIDATE,
                    0xE0: PdcFwSeries.TI_ENGINEERING,
                    # Type-B images
                    0xF2: PdcFwSeries.TI_PRODUCTION,
                    0xC2: PdcFwSeries.TI_RELEASE_CANDIDATE,
                    0xE2: PdcFwSeries.TI_ENGINEERING,
                }[series],
            )

        elif header == TiHeader.APPCONFIG_SECTION:
            # Standalone appconfig file. No FW version available.
            return PdcFwVer(
                vendor=PdcVendor.TI,
                series=PdcFwSeries.CONFIG_ONLY,
                major=None,
                minor=None,
                patch=None,
                project_name=format_ti_config_string(
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


def get_hash_bytes(binary_path: Path) -> bytes:
    """Generate hash file bytes for a TI binary."""
    ver = read_base_fw_ver_and_proj_name(binary_path)
    if ver.major is None:
        raise ValueError(f"Cannot read version from TI binary {binary_path}")
    if ver.project_name is None:
        raise ValueError(
            f"Cannot read project name from TI binary {binary_path}"
        )

    if ver.project_name.startswith("GOOG"):
        proj_bytes = ver.project_name.encode("ascii")
    elif ver.project_name.startswith("0x"):
        proj_bytes = binascii.unhexlify(ver.project_name[2:])
    else:
        raise ValueError(f"Unexpected project name format: {ver.project_name}")

    proj_bytes = proj_bytes.ljust(8, b"\x00")
    if len(proj_bytes) > 8:
        raise ValueError(f"Project name too long: {ver.project_name}")

    return bytes(ver.as_tuple()) + proj_bytes

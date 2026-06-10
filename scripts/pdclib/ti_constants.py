# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Defines constants relevant to TI PDC FW binaries"""

import enum


class TiHeader(bytes, enum.Enum):
    """TI PDC FW image headers"""

    TFU_BUNDLE_TYPE_A = b"\x03\x00\xef\xac"
    TFU_BUNDLE_TYPE_B = b"\x13\x00\xef\xac"
    APPCONFIG_SECTION = b"\x03\x00\xea\xac"


class TiFwOffset(enum.IntEnum):
    """Offsets to extract fields from TI FW binary"""

    FWVER_OFFSET = 0x4F4
    NUM_BLOCKS_OFFSET = 0x04
    FW_SIZE_OFFSET = 0x4F8
    PROJ_NAME_OFFSET = 30
    PROJ_NAME_LENGTH = 8
    HEADER_BLOCK_LENGTH = 0x800
    DATA_METADATA_LENGTH = 0x08
    METADATA_OFFSET = 0x04


class TiFwFormat(str, enum.Enum):
    """struct.unpack formats for TI FW binary fields"""

    FWVER = "BBBB"
    NUM_BLOCKS = "<H"
    FW_SIZE = "<I"

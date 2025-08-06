# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Defines constants relevant to Realtek PDC FW binaries"""

import enum


class RtkFwOffset(enum.IntEnum):
    """Offsets to extract certain fields from the RTK FW binary"""

    # Full config section location
    CONFIG_RANGE_START = 0x1F000
    CONFIG_RANGE_END = CONFIG_RANGE_START + 0x1000

    # Config section parameters
    USB_VID = 0x1F89E
    USB_VID_LEN = 2
    USB_PID = 0x1F8A0
    USB_PID_LEN = 2

    PROJECT_NAME = 0x1FC00
    PROJECT_NAME_LEN = 12

    FW_VERSION_MAJOR = 0x7EF9
    FW_VERSION_MINOR = 0x7EFA
    FW_VERSION_CONFIG = 0x1F802

    PORT_USED = 0x1F805

    # CRC32 signing
    CRC_OFFSET = 0x0001FFE6
    CRC_LEN = 4
    CRC_RANGE_START = 0
    CRC_RANGE_END = 0x1FFE6

    # Flash layout
    # 2 segments, each 64kiB, for a total of 128kiB
    SEGMENT_SIZE = 64 * 1024
    TOTAL_SIZE = 2 * SEGMENT_SIZE


class RtkPortUsed(enum.IntEnum):
    """Indicates which port(s) are used by the PDC config"""

    PORTB_ONLY = 0x00
    PORTA_ONLY = 0x01
    DUAL_PORT = 0x02

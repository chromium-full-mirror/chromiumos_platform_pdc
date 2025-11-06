# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cross-vendor definitions and utilities for PDC firmware binaries"""

import binascii
import dataclasses


@dataclasses.dataclass
class UsbVidPid:
    """Store a USB VID and PID"""

    vid: int
    pid: int

    def __str__(self):
        return f"{self.vid:04X}:{self.pid:04X}"


def print_hex(buffer, title=None, output_func=print):
    """Print a buffer as ASCII hex with 16 bytes per row"""
    if title:
        output_func(title)

    i = 0
    while i < len(buffer):
        row = buffer[i : min(i + 16, len(buffer))]
        output_func(binascii.hexlify(row, " ").decode("ascii"))
        i += 16


def add_pdclib_private():
    """Add pdclib_private to Python path.

    Only available to internal source checkouts.
    """

    import pathlib
    import sys

    pdclib_private_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent.parent
        / "ec-private"
        / "pdc"
    )

    if not pdclib_private_path.exists():
        raise RuntimeError(
            "This feature requires a chrome-internal source checkout"
        )

    sys.path.append(str(pdclib_private_path))

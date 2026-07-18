# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cross-vendor definitions and utilities for PDC firmware binaries"""

import binascii
import dataclasses


class ConfigName:
    """Parse an 8-character PDC config/project name string"""

    def __init__(self, config_name: str | bytes):
        if isinstance(config_name, bytes):
            config_name = config_name.decode("ascii")
        self.config_name = config_name

    @property
    def prefix(self) -> str:
        return self.config_name[0:4]

    @property
    def id(self) -> str:
        return self.config_name[4:6]

    @property
    def revision(self) -> str:
        return self.config_name[6]

    @property
    def variant(self) -> str:
        return self.config_name[7]

    def get_revision_zero_string(self) -> str:
        """Return the config name but with the revision set to 0"""
        return f"{self.prefix}{self.id}0{self.variant}"

    def compare_id_and_variant(self, other: "ConfigName") -> None:
        """Compare two config names for the same config ID and variant.

        This ignores the config revision field.

        Raises an AssertionError with a helpful message if comparison fails.
        """
        assert (
            self.prefix == other.prefix
        ), f"Prefixes differ ('{self.prefix}' != '{other.prefix}')"
        assert (
            self.id == other.id
        ), f"Config IDs differ ('{self.id}' != '{other.id}')"
        assert (
            self.variant == other.variant
        ), f"Config variants differ ('{self.variant}' != '{other.variant}')"

    def __eq__(self, other: "ConfigName") -> bool:
        return self.config_name == other.config_name

    def __str__(self):
        return self.config_name


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

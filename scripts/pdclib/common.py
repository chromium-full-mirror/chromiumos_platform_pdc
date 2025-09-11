# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cross-vendor definitions and utilities for PDC firmware binaries"""

import dataclasses


@dataclasses.dataclass
class UsbVidPid:
    """Store a USB VID and PID"""

    vid: int
    pid: int

    def __str__(self):
        return f"{self.vid:04X}:{self.pid:04X}"

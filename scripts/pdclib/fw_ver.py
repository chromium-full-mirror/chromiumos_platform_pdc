# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common object for storing PDC FW versions"""

import dataclasses
import enum
import json
from typing import Tuple


class PdcVendor(enum.Enum):
    """PDC vendors"""

    TI = enum.auto()
    RTK = enum.auto()


class PdcFwSeries(enum.Enum):
    """PDC FW series"""

    CONFIG_ONLY = enum.auto()
    RTK_BRINGUP = enum.auto()
    RTK_TEST = enum.auto()
    RTK_RELEASE = enum.auto()
    TI_ENGINEERING = enum.auto()
    TI_RELEASE_CANDIDATE = enum.auto()
    TI_PRODUCTION = enum.auto()

    def is_releasable(self) -> bool:
        """Whether FW from this series can be released on shipping boards"""
        return self in (
            PdcFwSeries.RTK_RELEASE,
            PdcFwSeries.TI_PRODUCTION,
        )


class PdcJsonEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles PdcFwVer objects"""

    def default(self, o):
        if isinstance(o, PdcFwVer):
            return dataclasses.asdict(o)
        elif isinstance(o, (PdcVendor, PdcFwSeries)):
            return o.name
        return super().default(o)


@dataclasses.dataclass
class PdcFwVer:
    """Cross-vendor PDC FW version object"""

    major: int
    minor: int
    patch: int
    project_name: str
    vendor: PdcVendor
    series: PdcFwSeries

    @property
    def config_ver(self) -> int:
        """Alias for patch version (applicable to RTK images)"""
        return self.patch

    def as_tuple(self) -> Tuple[int, int, int]:
        """Get a (major,minor,patch) tuple"""
        return (self.major, self.minor, self.patch)

    def as_full_tuple(self) -> Tuple[int, int, int]:
        """Get a (major,minor,patch, project_name) tuple"""
        return (*self.as_tuple(), self.project_name)

    def __str__(self) -> str:
        if self.major is None and self.minor is None:
            ver = f"x.x.{self.patch}"
        else:
            ver = f"{self.major}.{self.minor}.{self.patch}"

        return (
            f"{self.vendor.name} {ver} "
            f"({self.series.name}, {self.project_name})"
        )

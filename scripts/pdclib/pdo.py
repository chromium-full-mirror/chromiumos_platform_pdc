# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities for parsing Power Delivery Objects (PDOs)

Use PDO.parse_pdo() as a factory method for parsing a 32-bit PDO value and
instantiating the correct object.
"""

import enum


class PDORole(enum.Enum):
    """Enum for representing source versus sink PDOs"""

    SINK = 0
    SOURCE = 1


class PDOConstants(enum.IntEnum):
    """Bit offsets and other constants for parsing PDOs"""

    PDO_TYPE_OFFSET = 30
    PDO_TYPE_MASK = 0x3 << PDO_TYPE_OFFSET

    PDO_VOLT_UNITS_MV = 50
    PDO_CURRENT_UNITS_MA = 10
    PDO_POWER_UNITS_MW = 250

    #
    # Fixed PDOs only
    #

    PDO_FIXED_CURRENT_OFFSET = 0
    PDO_FIXED_CURRENT_MASK = 0x3FF << PDO_FIXED_CURRENT_OFFSET

    PDO_FIXED_VOLT_OFFSET = 10
    PDO_FIXED_VOLT_MASK = 0x3FF << PDO_FIXED_VOLT_OFFSET

    # Source PDO only - bits 20:21, bit 22 reserved, 23, 24
    # USB-PD R3.2 V1.0 Table 6.17
    PDO_FIXED_PEAK_CURRENT_OFFSET = 20
    PDO_FIXED_PEAK_CURRENT_MASK = 0x03 << PDO_FIXED_PEAK_CURRENT_OFFSET
    PDO_FIXED_EPR_CAPABLE = 1 << 23
    PDO_FIXED_UNCHUNKED_EXT_MSG_CAPABLE = 1 << 24

    # Sink PDO only - 24:23 FRS current, bits 22:20 reserved
    # USB-PD R3.2 V1.0 Table 6.17
    PDO_FIXED_FRS_CURRENT_OFFSET = 23
    PDO_FIXED_FRS_CURRENT_MASK = 0x3 << PDO_FIXED_FRS_CURRENT_OFFSET

    # Common to source and sink PDOs
    PDO_FIXED_DUAL_ROLE_DATA = 1 << 25
    PDO_FIXED_COMM_CAPABLE = 1 << 26
    PDO_FIXED_UNCONSTRAINED_POWER = 1 << 27
    PDO_FIXED_SUSPEND_CAPABLE = 1 << 28
    PDO_FIXED_DUALROLE_POWER = 1 << 29

    #
    # Battery PDOs only
    #

    PDO_BAT_POWER_OFFSET = 0
    PDO_BAT_POWER_MASK = 0x3FF << PDO_BAT_POWER_OFFSET

    PDO_BAT_MIN_VOLTAGE_OFFSET = 10
    PDO_BAT_MIN_VOLTAGE_MASK = 0x3FF << PDO_BAT_MIN_VOLTAGE_OFFSET

    PDO_BAT_MAX_VOLTAGE_OFFSET = 20
    PDO_BAT_MAX_VOLTAGE_MASK = 0x3FF << PDO_BAT_MAX_VOLTAGE_OFFSET

    #
    # Variable PDOs only
    #

    PDO_VAR_CURRENT_OFFSET = 0
    PDO_VAR_CURRENT_MASK = 0x3FF << PDO_VAR_CURRENT_OFFSET

    PDO_VAR_MIN_VOLTAGE_OFFSET = 10
    PDO_VAR_MIN_VOLTAGE_MASK = 0x3FF << PDO_VAR_MIN_VOLTAGE_OFFSET

    PDO_VAR_MAX_VOLTAGE_OFFSET = 20
    PDO_VAR_MAX_VOLTAGE_MASK = 0x3FF << PDO_VAR_MAX_VOLTAGE_OFFSET


class PDOType(enum.IntEnum):
    """Represents different types of PDOs"""

    FIX = 0
    BAT = 1
    VAR = 2
    AUG = 3

    @staticmethod
    def get_type_from_pdo(pdo: int) -> "PDOType":
        """Parse a PDO and extract the PDO type"""
        return PDOType(
            (pdo & PDOConstants.PDO_TYPE_MASK) >> PDOConstants.PDO_TYPE_OFFSET
        )


class PDOFixedFRSCurrent(enum.IntEnum):
    """FRS current field in a fixed PDO"""

    FRS_NOT_SUPPORTED = 0
    FRS_DEFAULT_USB_POWER = 1
    FRS_V5_1A5 = 2
    FRS_V5_3A0 = 3

    @staticmethod
    def get_frs_current_from_pdo(pdo: int) -> "PDOFixedFRSCurrent":
        """Parse a fixed PDO and extract the FRS current value"""
        return PDOFixedFRSCurrent(
            (pdo & PDOConstants.PDO_FIXED_FRS_CURRENT_MASK)
            >> PDOConstants.PDO_FIXED_FRS_CURRENT_OFFSET
        )


class PDOFixedPeakCurrent(enum.IntEnum):
    """Peak current field in a fixed PDO"""

    PEAK_100 = 0
    PEAK_110 = 1
    PEAK_125 = 2
    PEAK_150 = 3

    @staticmethod
    def get_peak_current_from_pdo(pdo: int) -> "PDOFixedPeakCurrent":
        """Parse a fixed PDO and extract the peak overcurrent value"""
        return PDOFixedPeakCurrent(
            (pdo & PDOConstants.PDO_FIXED_PEAK_CURRENT_MASK)
            >> PDOConstants.PDO_FIXED_PEAK_CURRENT_OFFSET
        )


class PDO:
    """Base class for a PDO object"""

    def __init__(self, pdo: int, role: PDORole):
        self.pdo = pdo
        self.role = role

    @staticmethod
    def parse_pdo(pdo: int, role: PDORole) -> "PDO":
        """Parse a PDO

        Given a 32-bit Power Delivery Object, parse it and return the
        appropriate subclass based on type of PDO
        """
        pdo_type = PDOType.get_type_from_pdo(pdo)

        return {
            PDOType.FIX: PDOFixed,
            PDOType.BAT: PDOBattery,
            PDOType.VAR: PDOVariable,
            PDOType.AUG: PDOAugmented,
        }[pdo_type](pdo, role)

    @property
    def pdo_type(self) -> PDOType:
        """Get the type of PDO"""
        return PDOType.get_type_from_pdo(self.pdo)

    def __eq__(self, other: "PDO") -> bool:
        return self.pdo == other.pdo

    def __hash__(self) -> int:
        return hash(self.pdo)


class PDOFixed(PDO):
    """Fixed PDO"""

    @property
    def millivolts(self) -> int:
        return PDOConstants.PDO_VOLT_UNITS_MV * (
            (self.pdo & PDOConstants.PDO_FIXED_VOLT_MASK)
            >> PDOConstants.PDO_FIXED_VOLT_OFFSET
        )

    @property
    def milliamps(self) -> int:
        return PDOConstants.PDO_CURRENT_UNITS_MA * (
            (self.pdo & PDOConstants.PDO_FIXED_CURRENT_MASK)
            >> PDOConstants.PDO_FIXED_CURRENT_OFFSET
        )

    @property
    def peak_current(self) -> PDOFixedPeakCurrent:
        if self.role != PDORole.SOURCE:
            raise ValueError("Peak overcurrent only defined in source PDOs")
        return PDOFixedPeakCurrent.get_peak_current_from_pdo(self.pdo)

    @property
    def epr_supported(self) -> bool:
        if self.role != PDORole.SOURCE:
            raise ValueError("EPR bit only defined in source PDOs")
        return bool(self.pdo & PDOConstants.PDO_FIXED_EPR_CAPABLE)

    @property
    def unchunked_ext_msg_supported(self) -> bool:
        if self.role != PDORole.SOURCE:
            raise ValueError("Unchunked bit only defined in source PDOs")
        return bool(self.pdo & PDOConstants.PDO_FIXED_UNCHUNKED_EXT_MSG_CAPABLE)

    @property
    def comm_capable(self) -> bool:
        return bool(self.pdo & PDOConstants.PDO_FIXED_COMM_CAPABLE)

    @property
    def dualrole_data(self) -> bool:
        return bool(self.pdo & PDOConstants.PDO_FIXED_DUAL_ROLE_DATA)

    @property
    def dualrole_power(self) -> bool:
        return bool(self.pdo & PDOConstants.PDO_FIXED_DUALROLE_POWER)

    @property
    def frs_current(self) -> PDOFixedFRSCurrent:
        if self.role != PDORole.SINK:
            raise ValueError("FRS current only defined in sink PDOs")
        return PDOFixedFRSCurrent.get_frs_current_from_pdo(self.pdo)

    @property
    def suspend_capable(self) -> bool:
        return bool(self.pdo & PDOConstants.PDO_FIXED_SUSPEND_CAPABLE)

    @property
    def unconstrained_power(self) -> bool:
        return bool(self.pdo & PDOConstants.PDO_FIXED_UNCONSTRAINED_POWER)

    @property
    def watts(self) -> float:
        """Derived wattage value"""
        return self.millivolts * self.milliamps / 1e6

    def __str__(self):
        output = (
            f"{self.pdo:08x}: {self.pdo_type.name} | "
            f"{self.millivolts:5}mV {self.milliamps:5}mA "
            f"{round(self.watts, 2):7}W | "
            f"{'DRP' if self.dualrole_power else '   '} "
            f"{'DRD' if self.dualrole_data else '   '} "
            f"{'USB' if self.comm_capable else '   '} "
            f"{'UP ' if self.unconstrained_power else '   '} "
            f"{'SUS' if self.suspend_capable else '   '} | "
        )

        if self.role == PDORole.SOURCE:
            output += (
                f"{'EPR' if self.epr_supported else '   '} "
                f"{'UCHNK' if self.unchunked_ext_msg_supported else '     '} "
                f"{self.peak_current.name} "
            )

        if self.role == PDORole.SINK:
            output += f"{self.frs_current.name} "

        return output.strip()


class PDOBattery(PDO):
    """Battery PDO"""

    @property
    def millivolts_max(self) -> int:
        return PDOConstants.PDO_VOLT_UNITS_MV * (
            (self.pdo & PDOConstants.PDO_BAT_MAX_VOLTAGE_MASK)
            >> PDOConstants.PDO_BAT_MAX_VOLTAGE_OFFSET
        )

    @property
    def millivolts_min(self) -> int:
        return PDOConstants.PDO_VOLT_UNITS_MV * (
            (self.pdo & PDOConstants.PDO_BAT_MIN_VOLTAGE_MASK)
            >> PDOConstants.PDO_BAT_MIN_VOLTAGE_OFFSET
        )

    @property
    def milliwatts(self) -> int:
        return PDOConstants.PDO_POWER_UNITS_MW * (
            (self.pdo & PDOConstants.PDO_BAT_POWER_MASK)
            >> PDOConstants.PDO_BAT_POWER_OFFSET
        )

    def __str__(self):
        return (
            f"{self.pdo:08x}: {self.pdo_type.name} | "
            f"{self.millivolts_min:5}mV-{self.millivolts_max:5}mV "
            f"{round(self.milliwatts/1000, 2):7}W"
        )


class PDOVariable(PDO):
    """Variable PDO"""

    @property
    def millivolts_max(self) -> int:
        return PDOConstants.PDO_VOLT_UNITS_MV * (
            (self.pdo & PDOConstants.PDO_VAR_MAX_VOLTAGE_MASK)
            >> PDOConstants.PDO_VAR_MAX_VOLTAGE_OFFSET
        )

    @property
    def millivolts_min(self) -> int:
        return PDOConstants.PDO_VOLT_UNITS_MV * (
            (self.pdo & PDOConstants.PDO_VAR_MIN_VOLTAGE_MASK)
            >> PDOConstants.PDO_VAR_MIN_VOLTAGE_OFFSET
        )

    @property
    def milliamps(self) -> int:
        return PDOConstants.PDO_CURRENT_UNITS_MA * (
            (self.pdo & PDOConstants.PDO_VAR_CURRENT_MASK)
            >> PDOConstants.PDO_VAR_CURRENT_OFFSET
        )

    def __str__(self):
        return (
            f"{self.pdo:08x}: {self.pdo_type.name} | "
            f"{self.millivolts_min:5}mV-{self.millivolts_max:5}mV "
            f"{self.milliamps:6}mA"
        )


class PDOAugmented(PDO):
    """Augmented PDO"""

    # Not implemented currently

    def __str__(self):
        return f"{self.pdo:08x}: {self.pdo_type.name}"

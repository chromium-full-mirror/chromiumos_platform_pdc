# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities for working with Realtek FW binaries"""

import binascii
import dataclasses
from pathlib import Path
import struct
from typing import Tuple

# pylint: disable=import-modules-only
from pdclib.common import UsbVidPid
from pdclib.rtk_constants import RtkDebugAccyGpioPolarity
from pdclib.rtk_constants import RtkFwOffset
from pdclib.rtk_constants import RtkI2cBusVoltage
from pdclib.rtk_constants import RtkPortUsed


class RtkFileSizeError(Exception):
    """Thrown if a FW binary has an unexpected size"""


@dataclasses.dataclass
class RtkFwVersion:
    """Store a RTK PDC FW version (major.minor.config)"""

    major: int
    minor: int
    config: int

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.config}"


class RtkFwBinary:
    """Utilities for examining a Realtek PDC firmware binary"""

    def __init__(self, fw_path: Path):
        self.fw_bin = bytearray()
        with open(fw_path, "rb") as f:
            while chunk := f.read(1024):
                self.fw_bin.extend(chunk)

        if self.get_size() != RtkFwOffset.TOTAL_SIZE:
            raise RtkFileSizeError(
                f"Unknown FW file. Expected {RtkFwOffset.TOTAL_SIZE} "
                f"bytes, got {self.get_size()} bytes"
            )

    def get_size(self):
        """Size of the FW binary in bytes"""
        return len(self.fw_bin)

    def get_file_crc32(self) -> int:
        """Read the CRC32 embedded in the FW binary"""
        return struct.unpack(
            "<L",
            self.get_range(RtkFwOffset.CRC_OFFSET, RtkFwOffset.CRC_LEN),
        )[0]

    def set_file_crc32(self):
        """Recalculate the CRC32 of the FW binary and update the stored value"""
        crc32 = self.calc_crc32()
        self.fw_bin[
            RtkFwOffset.CRC_OFFSET : RtkFwOffset.CRC_OFFSET
            + RtkFwOffset.CRC_LEN
        ] = bytearray(crc32.to_bytes(4, "little"))

    def calc_crc32(self) -> int:
        """Calculate the actual CRC32 of the FW binary"""
        return (
            binascii.crc32(
                self.fw_bin[
                    RtkFwOffset.CRC_RANGE_START : RtkFwOffset.CRC_RANGE_END
                ]
            )
            ^ 0xFFFFFFFF
        )

    def verify_crc32(self) -> bool:
        """Compare the expected and actual CRC32 checksums"""
        return self.calc_crc32() == self.get_file_crc32()

    def get_port_used(self) -> RtkPortUsed:
        """Get the 'port used' setting, which controls single vs double port"""
        return RtkPortUsed(self.fw_bin[RtkFwOffset.PORT_USED])

    def get_fw_version(self) -> Tuple[int, int, int]:
        """Get the version of the FW and config as tuple"""
        return RtkFwVersion(
            self.fw_bin[RtkFwOffset.FW_VERSION_MAJOR],
            self.fw_bin[RtkFwOffset.FW_VERSION_MINOR],
            self.fw_bin[RtkFwOffset.FW_VERSION_CONFIG],
        )

    def get_project_name(self) -> str | None:
        """Get the project name string from config section"""
        proj_name = self.get_range(
            RtkFwOffset.PROJECT_NAME, RtkFwOffset.PROJECT_NAME_LEN
        )

        try:
            return proj_name.decode("ascii").strip("\x00")
        except UnicodeDecodeError:
            # If project name field contains invalid characters, it is not
            # supported by this firmware version.
            return None

    def get_vid_pid(self) -> Tuple[int, int]:
        """Get the USB vendor ID (VID) and product ID (PID)"""
        return UsbVidPid(
            *struct.unpack(
                "<HH",
                self.get_range(RtkFwOffset.USB_VID, RtkFwOffset.USB_VID_LEN)
                + self.get_range(RtkFwOffset.USB_PID, RtkFwOffset.USB_PID_LEN),
            )
        )

    def get_debug_accy_gpio_polarity(self) -> RtkDebugAccyGpioPolarity:
        """Read the polarity of the debug accessory GPIO"""
        return RtkDebugAccyGpioPolarity(
            self.fw_bin[RtkFwOffset.DEBUG_ACCY_GPIO_POLARITY]
        )

    def get_pmc_i2c_addrs(self) -> Tuple[int, int]:
        """Read the base PMC I2C address

        Note: the addresses are returned as a tuple (Port A, Port B) in
        7-bit format.
        """

        return (
            self.fw_bin[RtkFwOffset.PMC_I2C_ADDR_PORTA] >> 1,
            self.fw_bin[RtkFwOffset.PMC_I2C_ADDR_PORTB] >> 1,
        )

    def get_retimer_i2c_addrs(self) -> Tuple[int, int]:
        """Read the I2C addresses of the retimer(s)

        Note: the addresses are returned as a tuple (Port A, Port B) in
        7-bit format.
        """

        return (
            self.fw_bin[RtkFwOffset.RETIMER_I2C_ADDR_PORTA] >> 1,
            self.fw_bin[RtkFwOffset.RETIMER_I2C_ADDR_PORTB] >> 1,
        )

    def get_bbr_i2c_addrs(self) -> Tuple[int, int]:
        """Read the I2C addresses of Burnside Bridge (BBR) retimers

        Note: the addresses are returned as a tuple (Port A, Port B) in
        7-bit format.
        """

        return (
            self.fw_bin[RtkFwOffset.BBR_I2C_ADDR_PORTA] >> 1,
            self.fw_bin[RtkFwOffset.BBR_I2C_ADDR_PORTB] >> 1,
        )

    def get_i2c_voltage_smbus(self) -> RtkI2cBusVoltage:
        """Read the voltage level of the SMBus/EC I2C interface"""

        return RtkI2cBusVoltage(self.fw_bin[RtkFwOffset.I2C_VOLTAGE_SMBUS])

    def get_i2c_voltage_retimer(self) -> RtkI2cBusVoltage:
        """Read the voltage level of the retimer I2C interface"""

        return RtkI2cBusVoltage(self.fw_bin[RtkFwOffset.I2C_VOLTAGE_RETIMER])

    def get_i2c_voltage_pmc(self) -> RtkI2cBusVoltage:
        """Read the voltage level of the PMC I2C interface"""

        return RtkI2cBusVoltage(self.fw_bin[RtkFwOffset.I2C_VOLTAGE_PMC])

    def get_range(self, start_offset: int, length: int) -> bytes:
        """Read a chunk of the FW binary"""
        if not (
            0 <= start_offset < len(self.fw_bin)
            and 0 <= (start_offset + length) <= len(self.fw_bin)
        ):
            raise ValueError(
                f"Offset ({start_offset}) or length ({length}) are out of range"
            )

        return self.fw_bin[start_offset : start_offset + length]

    def set_config(self, config: bytearray):
        """Overwrites the config region of a Realtek FW binary"""
        if (
            len(config)
            != RtkFwOffset.CONFIG_RANGE_END - RtkFwOffset.CONFIG_RANGE_START
        ):
            raise ValueError(
                f"Config length ({len(config)}) does not match expected size "
                f"({RtkFwOffset.CONFIG_RANGE_SIZE})"
            )
        self.fw_bin[
            RtkFwOffset.CONFIG_RANGE_START : RtkFwOffset.CONFIG_RANGE_END
        ] = config

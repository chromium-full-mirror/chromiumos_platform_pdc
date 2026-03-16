# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities for working with Realtek FW binaries"""

import binascii
import dataclasses
import hashlib
from pathlib import Path
import struct
from typing import Iterable, List, Tuple

# pylint: disable=import-modules-only
from pdclib.common import UsbVidPid
from pdclib.pdo import PDO
from pdclib.pdo import PDORole
from pdclib.rtk_constants import RtkChipType
from pdclib.rtk_constants import RtkConfigOffset
from pdclib.rtk_constants import RtkDebugAccyGpioPolarity
from pdclib.rtk_constants import RtkFwOffset
from pdclib.rtk_constants import RtkI2cBusVoltage
from pdclib.rtk_constants import RtkPortSbuMuxConfig
from pdclib.rtk_constants import RtkPortUsed
from pdclib.rtk_constants import RtkRetimerConfig


class RtkFileSizeError(Exception):
    """Thrown if a FW binary has an unexpected size"""


@dataclasses.dataclass
class RtkFwVersion:
    """Store a RTK PDC FW version (major.minor.config)"""

    major: int
    minor: int
    config: int

    def as_tuple(self) -> tuple:
        return (self.major, self.minor, self.config)

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.config}"


def _range_check(arr: bytearray, start: int, length: int) -> None:
    """Helper to throw an exception if a range is out of bounds"""

    if not (0 <= start < len(arr) and 0 <= (start + length) <= len(arr)):
        raise ValueError(
            f"Offset ({start}) or length ({length}) are out of range "
            f"(total len {len(arr)})"
        )


class _RtkConfigMixin:
    """Provides methods for reading a RTK config section.

    This is an abstract class intended to be mixed-in to another class. Its
    subclasses shall implement `_get_config_region_location()` to access the
    underlying config section data by reference.
    """

    def _get_config_region_location(self) -> Tuple[bytearray, int]:
        """Implement in the inheriting class

        Should provide a reference to the bytearray containing the config data,
        and a start offset within the bytearray where the config regions starts.
        """
        raise NotImplementedError()

    def _get_config_range(self, start_offset: int, length: int) -> bytearray:
        """Read a chunk of the config section"""
        config_fragment, offset = self._get_config_region_location()

        start_offset += offset

        _range_check(config_fragment, start_offset, length)
        return config_fragment[start_offset : start_offset + length]

    def _get_config_byte(self, offset: int) -> int:
        """Read a single byte from the config section"""
        return self._get_config_range(offset, 1)[0]

    def get_port_used(self) -> RtkPortUsed:
        """Get the 'port used' setting, which controls single vs double port"""
        return RtkPortUsed(self._get_config_byte(RtkConfigOffset.PORT_USED))

    def get_project_name(self) -> str | None:
        """Get the project name string from config section"""
        proj_name = self._get_config_range(
            RtkConfigOffset.PROJECT_NAME, RtkConfigOffset.PROJECT_NAME_LEN
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
                self._get_config_range(
                    RtkConfigOffset.USB_VID, RtkConfigOffset.USB_VID_LEN
                )
                + self._get_config_range(
                    RtkConfigOffset.USB_PID, RtkConfigOffset.USB_PID_LEN
                ),
            )
        )

    def get_debug_accy_gpio_polarity(self) -> RtkDebugAccyGpioPolarity:
        """Read the polarity of the debug accessory GPIO"""
        return RtkDebugAccyGpioPolarity(
            self._get_config_byte(RtkConfigOffset.DEBUG_ACCY_GPIO_POLARITY)
        )

    def get_pmc_i2c_addrs(self) -> Tuple[int, int]:
        """Read the base PMC I2C address

        Note: the addresses are returned as a tuple (Port A, Port B) in
        7-bit format.
        """

        return (
            self._get_config_byte(RtkConfigOffset.PMC_I2C_ADDR_PORTA) >> 1,
            self._get_config_byte(RtkConfigOffset.PMC_I2C_ADDR_PORTB) >> 1,
        )

    def get_retimer_i2c_addrs(self) -> Tuple[int, int]:
        """Read the I2C addresses of the retimer(s)

        Note: the addresses are returned as a tuple (Port A, Port B) in
        7-bit format.
        """

        return (
            self._get_config_byte(RtkConfigOffset.RETIMER_I2C_ADDR_PORTA) >> 1,
            self._get_config_byte(RtkConfigOffset.RETIMER_I2C_ADDR_PORTB) >> 1,
        )

    def get_bbr_i2c_addrs(self) -> Tuple[int, int]:
        """Read the I2C addresses of Burnside Bridge (BBR) retimers

        Note: the addresses are returned as a tuple (Port A, Port B) in
        7-bit format.
        """

        return (
            self._get_config_byte(RtkConfigOffset.BBR_I2C_ADDR_PORTA) >> 1,
            self._get_config_byte(RtkConfigOffset.BBR_I2C_ADDR_PORTB) >> 1,
        )

    def get_chip_type(self) -> RtkChipType:
        """return if the chip is rts545x-vb."""

        if (
            self._get_config_byte(RtkConfigOffset.FW_CONFIG_CHIP_ID_L) == 0x39
            and self._get_config_byte(RtkConfigOffset.FW_CONFIG_CHIP_ID_H)
            == 0x69
        ):
            return RtkChipType.RTS545X
        if (
            self._get_config_byte(RtkConfigOffset.FW_CONFIG_CHIP_ID_L) == 0x07
            and self._get_config_byte(RtkConfigOffset.FW_CONFIG_CHIP_ID_H)
            == 0x70
        ):
            return RtkChipType.RTS545X_VB
        return RtkChipType.UNKNOWN

    def get_config_version(self) -> int:
        """Read the config version"""
        return self._get_config_byte(RtkConfigOffset.FW_VERSION_CONFIG)

    def get_i2c_voltage_smbus(self) -> RtkI2cBusVoltage:
        """Read the voltage level of the SMBus/EC I2C interface"""

        return RtkI2cBusVoltage.parse_from_config(
            self._get_config_byte(RtkConfigOffset.I2C_VOLTAGE_SMBUS),
            self.get_chip_type(),
        )

    def get_i2c_voltage_retimer(self) -> RtkI2cBusVoltage:
        """Read the voltage level of the retimer I2C interface"""

        return RtkI2cBusVoltage.parse_from_config(
            self._get_config_byte(RtkConfigOffset.I2C_VOLTAGE_RETIMER),
            self.get_chip_type(),
        )

    def get_i2c_voltage_pmc(self) -> RtkI2cBusVoltage:
        """Read the voltage level of the PMC I2C interface"""

        return RtkI2cBusVoltage.parse_from_config(
            self._get_config_byte(RtkConfigOffset.I2C_VOLTAGE_PMC),
            self.get_chip_type(),
        )

    def get_pdos(self, role: PDORole, port: str) -> List[PDO]:
        """Get the source or sink PDOs stored in the config"""

        if port == "A" and role == PDORole.SINK:
            count_offset = RtkConfigOffset.SNK_PDO_COUNT_PORTA
            start_offset = RtkConfigOffset.SNK_PDO_OFFSET_PDO1_PORTA
        elif port == "B" and role == PDORole.SINK:
            count_offset = RtkConfigOffset.SNK_PDO_COUNT_PORTB
            start_offset = RtkConfigOffset.SNK_PDO_OFFSET_PDO1_PORTB
        elif port == "A" and role == PDORole.SOURCE:
            count_offset = RtkConfigOffset.SRC_PDO_COUNT_PORTA
            start_offset = RtkConfigOffset.SRC_PDO_OFFSET_PDO1_PORTA
        elif port == "B" and role == PDORole.SOURCE:
            count_offset = RtkConfigOffset.SRC_PDO_COUNT_PORTB
            start_offset = RtkConfigOffset.SRC_PDO_OFFSET_PDO1_PORTB
        else:
            raise ValueError(
                "port must be 'A' or 'B' and 'role' must be "
                "PDORole.SINK or PDORole.SOURCE"
            )

        count = min(
            RtkConfigOffset.PDO_MAX_COUNT, self._get_config_byte(count_offset)
        )

        return [
            PDO.parse_pdo(
                struct.unpack("<I", self._get_config_range(i, 4))[0], role
            )
            for i in range(start_offset, start_offset + 4 * count, 4)
        ]

    def get_src_max_pdp(self, port: str) -> int:
        """Get the max source PDP value for each port"""
        if port == "A":
            return self._get_config_byte(RtkConfigOffset.SRC_MAX_PDP_PORTA)
        elif port == "B":
            return self._get_config_byte(RtkConfigOffset.SRC_MAX_PDP_PORTB)
        else:
            raise ValueError("port must be 'A' or 'B'")

    def get_svids(self, port: str) -> List[int]:
        """Get the SVIDs stored in the config, by port"""

        if port == "A":
            count_offset = RtkConfigOffset.SVID_COUNT_PORTA
            start_offset = RtkConfigOffset.SVID_OFFSET_PORTA
        elif port == "B":
            count_offset = RtkConfigOffset.SVID_COUNT_PORTB
            start_offset = RtkConfigOffset.SVID_OFFSET_PORTB
        else:
            raise ValueError("port must be 'A' or 'B'")

        count = min(
            RtkConfigOffset.SVID_MAX_COUNT, self._get_config_byte(count_offset)
        )

        return [
            struct.unpack("<H", self._get_config_range(i, 2))[0]
            for i in range(start_offset, start_offset + 2 * count, 2)
        ]

    def get_port_sbumux_config(self, port: str):
        """Read SBU mux config register"""
        if port == "A":
            value = self._get_config_byte(RtkConfigOffset.SBUMUX_CFG_PORTA)
        elif port == "B":
            value = self._get_config_byte(RtkConfigOffset.SBUMUX_CFG_PORTB)
        else:
            raise ValueError("port must be 'A' or 'B'")

        return RtkPortSbuMuxConfig(value)

    def get_config(self) -> bytes:
        """Read full config"""
        return self._get_config_range(
            RtkConfigOffset.CONFIG_RANGE_START,
            RtkConfigOffset.CONFIG_RANGE_LENGTH,
        )

    def get_config_hash(self) -> str:
        """Return the SHA1 of the config region"""
        return hashlib.sha1(self.get_config()).hexdigest()

    def export_config_section(self, filepath: Path):
        """Write the config section to a file"""
        filepath.write_bytes(self.get_config())

    def compare_configs(self, other: "_RtkConfigMixin") -> bool:
        """Compare two config regions for equivalence. Ignore certain fields"""

        this_config = self.get_config()
        other_config = other.get_config()

        if (
            len(this_config) != RtkConfigOffset.CONFIG_RANGE_LENGTH
            or len(other_config) != RtkConfigOffset.CONFIG_RANGE_LENGTH
        ):
            raise ValueError(
                f"Config section has bad length (self={len(this_config)}, "
                f"other={len(other_config)}, "
                f"expected={RtkConfigOffset.CONFIG_RANGE_LENGTH})"
            )

        # Special fields that are preserved when overwriting a config. A config
        # comparison should ignore these.
        IGNORE_OFFSETS = {
            RtkConfigOffset.FW_CONFIG_VERSION_MAJOR,
            RtkConfigOffset.FW_CONFIG_VERSION_MINOR,
            RtkConfigOffset.FW_CONFIG_CHIP_ID_L,
            RtkConfigOffset.FW_CONFIG_CHIP_ID_H,
        }

        return all(
            x == y
            for i, (x, y) in enumerate(zip(this_config, other_config))
            if i not in IGNORE_OFFSETS
        )


class RtkConfigFragment(_RtkConfigMixin):
    """Stores a standalone config fragment."""

    def __init__(self, filepath: Path):
        config_fragment = filepath.read_bytes()

        if len(config_fragment) != RtkConfigOffset.CONFIG_RANGE_LENGTH:
            raise ValueError(
                "Config fragment has unexpected length: "
                f"Got {len(config_fragment)}, "
                f"expected {RtkConfigOffset.CONFIG_RANGE_LENGTH}"
            )

        self.config_fragment = config_fragment

    # @override
    def _get_config_region_location(self) -> Tuple[bytearray, int]:
        """Provide a reference to the config fragment bytearray

        Used by the mixin's methods to access the underlying config data
        """
        return self.config_fragment, 0


class RtkFwBinary(_RtkConfigMixin):
    """Utilities for examining a Realtek PDC firmware binary

    This class mixes in RtkConfigBinary, so all of its methods are directly
    available. _get_config_region_location() is overridden to remap the config
    data location to where it appears in the full FW binary.
    """

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

        # Do not initialize the superclass (RtkConfigBinary). Just allow its
        # methods to mix-in and override _get_config_region_location() so those
        # methods read from self.fw_bin with an overall config section offset
        # added.

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
                self.get_range(
                    RtkFwOffset.CRC_RANGE_START, RtkFwOffset.CRC_RANGE_LENGTH
                )
            )
            ^ 0xFFFFFFFF
        )

    def verify_crc32(self) -> bool:
        """Compare the expected and actual CRC32 checksums"""
        return self.calc_crc32() == self.get_file_crc32()

    def get_fw_version(self) -> RtkFwVersion:
        """Get the version of the FW and config"""
        return RtkFwVersion(
            self.get_byte(RtkFwOffset.FW_VERSION_MAJOR),
            self.get_byte(RtkFwOffset.FW_VERSION_MINOR),
            self.get_config_version(),
        )

    def get_range(self, start_offset: int, length: int) -> bytes:
        """Read a chunk of the FW binary"""
        _range_check(self.fw_bin, start_offset, length)
        return self.fw_bin[start_offset : start_offset + length]

    def get_byte(self, offset: int) -> int:
        """Read a single byte from the FW binary"""
        return self.get_range(offset, 1)[0]

    # @override
    def _get_config_region_location(self) -> Tuple[bytearray, int]:
        """Provides _RtkConfigMixin access to the config data

        Pass a reference to fw_bin with an offset to the start of the config
        section within the FW binary.
        """
        return self.fw_bin, RtkFwOffset.CONFIG_RANGE_START

    def get_base_firmware_hash(self) -> str:
        """Return the SHA1 of the base firmware region"""
        return hashlib.sha1(
            self.get_range(
                RtkFwOffset.FW_CODE_START, RtkFwOffset.FW_CODE_LENGTH
            )
        ).hexdigest()

    def set_config(self, config: _RtkConfigMixin, preserve_version=True):
        """Overwrites the config region of a Realtek FW binary

        :param: config - Realtek configuration class. Can be a full FW binary
                or a config fragment.
        :param: preserve_version - If true, do not overwrite the major/minor
                version fields and the two chip ID bytes. If true, throw an
                exception if the config version field does not match between
                the base firmware and the config fragment.
        """
        config_fragment = config.get_config()

        if preserve_version:
            # Verify the config version matches
            if self.get_config_version() != config.get_config_version():
                raise ValueError(
                    "Config version mismatch: "
                    f"base firmware version {self.get_config_version()}, "
                    f"config version {config.get_config_version()}"
                )

        config_ver_major = self._get_config_byte(
            RtkConfigOffset.FW_CONFIG_VERSION_MAJOR
        )
        config_ver_minor = self._get_config_byte(
            RtkConfigOffset.FW_CONFIG_VERSION_MINOR
        )
        config_chip_id_l = self._get_config_byte(
            RtkConfigOffset.FW_CONFIG_CHIP_ID_L
        )
        config_chip_id_h = self._get_config_byte(
            RtkConfigOffset.FW_CONFIG_CHIP_ID_H
        )

        self.fw_bin[
            RtkFwOffset.CONFIG_RANGE_START : RtkFwOffset.CONFIG_RANGE_END
        ] = config_fragment

        if preserve_version:
            # Restore some fields to their original values
            self.fw_bin[
                RtkFwOffset.CONFIG_RANGE_START
                + RtkConfigOffset.FW_CONFIG_VERSION_MAJOR
            ] = config_ver_major
            self.fw_bin[
                RtkFwOffset.CONFIG_RANGE_START
                + RtkConfigOffset.FW_CONFIG_VERSION_MINOR
            ] = config_ver_minor
            self.fw_bin[
                RtkFwOffset.CONFIG_RANGE_START
                + RtkConfigOffset.FW_CONFIG_CHIP_ID_L
            ] = config_chip_id_l
            self.fw_bin[
                RtkFwOffset.CONFIG_RANGE_START
                + RtkConfigOffset.FW_CONFIG_CHIP_ID_H
            ] = config_chip_id_h

    def export_fw_binary(self, path: Path):
        """Save the full firmware binary to a file"""

        if self.get_size() != RtkFwOffset.TOTAL_SIZE:
            raise RtkFileSizeError(
                f"Expected {RtkFwOffset.TOTAL_SIZE} "
                f"bytes, got {self.get_size()} bytes"
            )

        path.write_bytes(self.fw_bin)


def fw_or_config_from_file(filepath: Path) -> RtkFwBinary | RtkConfigFragment:
    """Read a RtkFwBinary or RtkConfigFragment from file

    The type is determined automatically by file size.
    """

    size = filepath.stat().st_size

    if size == RtkFwOffset.CONFIG_RANGE_LENGTH:
        # Loading just a config fragment
        return RtkConfigFragment(filepath)
    if size == RtkFwOffset.TOTAL_SIZE:
        # Loading a full FW bundle.
        return RtkFwBinary(filepath)

    raise RtkFileSizeError(
        f"Size of {filepath} ({size} bytes) matches neither full binary nor "
        "config fragment lengths"
    )


def print_config(binary: RtkFwBinary | RtkConfigFragment, output_func=print):
    """Parse firmware binary or config fragment, printing out key config values

    Args:
        binary: RtkFwBinary containing the full Realtek firmware binary or a
                RtkConfigFragment containing only a config section.
        output_func: Function to call to output lines. Defaults to print().
                     Should automatically apply newlines.
    """

    if not isinstance(binary, _RtkConfigMixin):
        raise TypeError("Param `binary` must inherit _RtkConfigMixin")

    is_full_fw_binary = isinstance(binary, RtkFwBinary)

    def format_i2c_addrs(addrs: Iterable[int]) -> str:
        return ", ".join([hex(i) for i in addrs])

    def format_svid(svid: int) -> str:
        COMMON_SVIDS = {
            0xFF01: "DP (ff01)",
            0x8087: "TBT (8087)",
        }

        return COMMON_SVIDS.get(svid, hex(svid))

    def format_sbumux_cfg(port: str):
        val = binary.get_port_sbumux_config(port)
        str_val = RtkRetimerConfig(val).name or RtkPortSbuMuxConfig(val).name
        return f"0x{int(val):02x}: {str_val}"

    def format_crc32():
        if not is_full_fw_binary:
            return "N/A"

        return (
            f"{hex(binary.get_file_crc32())} "
            f"{'VALID' if binary.verify_crc32() else 'INVALID'}"
        )

    rtk_configs = {
        "Project name": binary.get_project_name(),
        "Chip type": binary.get_chip_type().name,
        "Version": (
            binary.get_fw_version()
            if is_full_fw_binary
            else f"x.x.{binary.get_config_version()}"
        ),
        "USB VID:PID": binary.get_vid_pid(),
        "Port config": binary.get_port_used().name,
        "Debug Accy GPIO": binary.get_debug_accy_gpio_polarity().name,
        "PMC I2C Base addrs": format_i2c_addrs(binary.get_pmc_i2c_addrs()),
        "Retimer I2C addrs": format_i2c_addrs(binary.get_retimer_i2c_addrs()),
        "BBR I2C addrs": format_i2c_addrs(binary.get_bbr_i2c_addrs()),
        "SMBus I2C voltage": binary.get_i2c_voltage_smbus().name,
        "Retimer I2C voltage": binary.get_i2c_voltage_retimer().name,
        "PMC I2C voltage": binary.get_i2c_voltage_pmc().name,
        "SVIDs Port A": ", ".join(
            (format_svid(svid) for svid in binary.get_svids("A"))
        ),
        "SVIDs Port B": ", ".join(
            (format_svid(svid) for svid in binary.get_svids("B"))
        ),
        "SBU Mux Port A": format_sbumux_cfg("A"),
        "SBU Mux Port B": format_sbumux_cfg("B"),
        "CRC32": format_crc32(),
        "Base FW SHA1": (
            binary.get_base_firmware_hash() if is_full_fw_binary else "N/A"
        ),
        "Config SHA1": binary.get_config_hash(),
    }

    for name, value in rtk_configs.items():
        output_func(f"{name.ljust(20)}: {value}")

    output_func("Sink PDOs Port A:")
    for p in binary.get_pdos(PDORole.SINK, "A"):
        output_func(str(p))

    output_func("Sink PDOs Port B:")
    for p in binary.get_pdos(PDORole.SINK, "B"):
        output_func(str(p))

    output_func(
        f"Source PDOs Port A: (Max PDP = {binary.get_src_max_pdp('A')}W)"
    )
    for p in binary.get_pdos(PDORole.SOURCE, "A"):
        output_func(str(p))

    output_func(
        f"Source PDOs Port B: (Max PDP = {binary.get_src_max_pdp('B')}W)"
    )
    for p in binary.get_pdos(PDORole.SOURCE, "B"):
        output_func(str(p))

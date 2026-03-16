# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Defines constants relevant to Realtek PDC FW binaries"""

import enum


class RtkFwOffset(enum.IntEnum):
    """Offsets to extract certain fields from the RTK FW binary"""

    # Full config section location
    CONFIG_RANGE_START = 0x1F800
    CONFIG_RANGE_END = 0x1FC60
    CONFIG_RANGE_LENGTH = CONFIG_RANGE_END - CONFIG_RANGE_START

    FW_CODE_START = 0
    FW_CODE_END = CONFIG_RANGE_START
    FW_CODE_LENGTH = FW_CODE_END - FW_CODE_START

    FW_VERSION_MAJOR = 0x7EF9
    FW_VERSION_MINOR = 0x7EFA
    # Note: the third version byte is RtkConfigOffset.FW_VERSION_CONFIG

    # CRC32 signing
    CRC_OFFSET = 0x0001FFE6
    CRC_LEN = 4
    CRC_RANGE_START = 0
    CRC_RANGE_END = 0x1FFE6
    CRC_RANGE_LENGTH = CRC_RANGE_END - CRC_RANGE_START

    # Flash layout
    # 2 segments, each 64kiB, for a total of 128kiB
    SEGMENT_SIZE = 64 * 1024
    TOTAL_SIZE = 2 * SEGMENT_SIZE


class RtkConfigOffset(enum.IntEnum):
    """Offsets within the config section"""

    CONFIG_RANGE_START = 0
    CONFIG_RANGE_END = RtkFwOffset.CONFIG_RANGE_LENGTH
    CONFIG_RANGE_LENGTH = CONFIG_RANGE_END - CONFIG_RANGE_START

    # Redundant version info stored in the config area. Read
    # RtkFwOffset.FW_VERSION_MAJOR, RtkFwOffset.FW_VERSION_MINOR
    # instead.
    FW_CONFIG_VERSION_MAJOR = 0x00
    FW_CONFIG_VERSION_MINOR = 0x01
    FW_VERSION_CONFIG = 0x02

    FW_CONFIG_CHIP_ID_L = 0x03
    FW_CONFIG_CHIP_ID_H = 0x04

    PORT_USED = 0x05

    SRC_MAX_PDP_PORTB = 0x0E  # Port 0
    SRC_MAX_PDP_PORTA = 0x0F  # Port 1

    PDO_MAX_COUNT = 7

    # Src PDOs
    SRC_PDO_COUNT_PORTB = 0x10  # Port 0
    SRC_PDO_COUNT_PORTA = 0x11  # Port 1
    SRC_PDO_OFFSET_PDO1_PORTB = 0x12  # Port 0 - start of 7*32-bit PDOs
    SRC_PDO_OFFSET_PDO1_PORTA = 0x2E  # Port 1 - start of 7*32-bit PDOs

    # Sink PDOs
    SNK_PDO_COUNT_PORTB = 0x4D  # Port 0
    SNK_PDO_COUNT_PORTA = 0x4E  # Port 1
    SNK_PDO_OFFSET_PDO1_PORTB = 0x4F  # POrt 0 - start of 7*32-bit PDOs
    SNK_PDO_OFFSET_PDO1_PORTA = 0x6B  # Port 1 - start of 7*32-bit PDOs

    # SVIDs
    SVID_MAX_COUNT = 4
    SVID_COUNT_PORTB = 0x8C  # Port 0
    SVID_COUNT_PORTA = 0x8D  # Port 1
    SVID_OFFSET_PORTB = 0x8E  # Port 0
    SVID_OFFSET_PORTA = 0x96  # Port 1

    USB_VID = 0x9E
    USB_VID_LEN = 2
    USB_PID = 0xA0
    USB_PID_LEN = 2

    I2C_VOLTAGE_SMBUS = 0xA8
    I2C_VOLTAGE_RETIMER = 0xA9
    I2C_VOLTAGE_PMC = 0xAA

    PMC_I2C_ADDR_PORTB = 0xAC  # Port 0
    PMC_I2C_ADDR_PORTA = 0xAD  # Port 1
    BBR_I2C_ADDR_PORTB = 0xAF  # Port 0
    BBR_I2C_ADDR_PORTA = 0xB4  # Port 1

    RETIMER_I2C_ADDR_PORTB = 0xB9  # Port 0
    RETIMER_I2C_ADDR_PORTA = 0xBE  # Port 1

    PROJECT_NAME = 0x400
    PROJECT_NAME_LEN = 12

    DEBUG_ACCY_GPIO_POLARITY = 0x40C

    SBUMUX_CFG_PORTB = 0x2C3
    SBUMUX_CFG_PORTA = 0x2C4


class RtkPortUsed(enum.IntEnum):
    """Indicates which port(s) are used by the PDC config"""

    PORTB_ONLY = 0x00
    PORTA_ONLY = 0x01
    DUAL_PORT = 0x02


class RtkDebugAccyGpioPolarity(enum.IntEnum):
    """Debug accessory detect GPIO polarity

    Indicates the polarity of the GPIO toggled in response to USB-C
    debug accessory mode being entered. Used to control CCD entry.
    """

    ACTIVE_LOW = 0x00
    ACTIVE_HIGH = 0x01
    DISABLED = 0xFF


class RtkChipType(enum.IntEnum):
    """Realtek PDC chip type"""

    UNKNOWN = 0
    RTS545X = 1
    RTS545X_VB = 2


class RtkI2cBusVoltage(enum.IntEnum):
    """Voltage level used on the PDC I2C interfaces (SMBus/EC, PMC, Retimer)"""

    LEVEL_1V8 = 0
    LEVEL_3V3 = 1

    @classmethod
    def parse_from_config(cls, value: int, chip_type: RtkChipType):
        if chip_type == RtkChipType.RTS545X:
            return {
                0: cls.LEVEL_1V8,
                1: cls.LEVEL_3V3,
            }[value]
        elif chip_type == RtkChipType.RTS545X_VB:
            return {
                0: cls.LEVEL_3V3,
                1: cls.LEVEL_1V8,
            }[value]
        raise ValueError("Unknown chip type")


class RtkPortSbuMuxConfig(enum.IntFlag):
    """Realtek SBU mux configuration bitfield

    This is used to configure the PDC to be compatible with various retimer
    parts. See http://b/479237337#comment15 for more info
    """

    # Let the PDC handle the SBU mux
    BYPASS_MODE = enum.auto()
    # Enable level-shifting of the SBU lines to 1.2V
    SBX_1V2 = enum.auto()
    # Enable level-shifting of the SBU lines to 1.8V
    SBX_1V8 = enum.auto()
    # Always route SBU lines to the Sideband (SBX) port
    SWITCH_TO_SBX = enum.auto()
    # Always route SBU lines to the AUX port
    SWITCH_TO_AUX = enum.auto()
    # Do not automatically flip the SBU lines' orientation
    DO_NOT_FLIP = enum.auto()


class RtkRetimerConfig(enum.IntFlag):
    """Common values for the SBU mux config field"""

    RETIMER_JBR = RtkPortSbuMuxConfig.BYPASS_MODE
    RETIMER_HBR = (
        RtkPortSbuMuxConfig.SWITCH_TO_AUX | RtkPortSbuMuxConfig.DO_NOT_FLIP
    )
    RETIMER_TI = RtkPortSbuMuxConfig.SWITCH_TO_AUX

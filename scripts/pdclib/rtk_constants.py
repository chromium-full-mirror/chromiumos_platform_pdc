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

    # Redundant version info stored in the config area. Read
    # FW_VERSION_MAJOR, FW_VERSION_MINOR instead.
    FW_CONFIG_VERSION_MAJOR = 0x1F800
    FW_CONFIG_VERSION_MINOR = 0x1F801

    FW_CONFIG_CHIP_ID_L = 0x1F803
    FW_CONFIG_CHIP_ID_H = 0x1F804

    PORT_USED = 0x1F805
    DEBUG_ACCY_GPIO_POLARITY = 0x1FC0C

    PMC_I2C_ADDR_PORTA = 0x1F8AD  # Port 1
    PMC_I2C_ADDR_PORTB = 0x1F8AC  # Port 0
    RETIMER_I2C_ADDR_PORTA = 0x1F8BE  # Port 1
    RETIMER_I2C_ADDR_PORTB = 0x1F8B9  # Port 0
    BBR_I2C_ADDR_PORTA = 0x1F8B4  # Port 1
    BBR_I2C_ADDR_PORTB = 0x1F8AF  # Port 0

    I2C_VOLTAGE_SMBUS = 0x1F8A8
    I2C_VOLTAGE_RETIMER = 0x1F8A9
    I2C_VOLTAGE_PMC = 0x1F8AA

    # SVIDs
    SVID_MAX_COUNT = 4
    SVID_COUNT_PORTA = 0x1F88D  # Port 1
    SVID_COUNT_PORTB = 0x1F88C  # Port 0
    SVID_OFFSET_PORTA = 0x1F896  # Port 1
    SVID_OFFSET_PORTB = 0x1F88E  # Port 0

    PDO_MAX_COUNT = 7

    # Sink PDOs
    SNK_PDO_COUNT_PORTA = 0x1F84E  # Port 1
    SNK_PDO_COUNT_PORTB = 0x1F84D  # Port 0
    SNK_PDO_OFFSET_PDO1_PORTA = 0x1F86B  # Port 1 - start of 7*32-bit PDOs
    SNK_PDO_OFFSET_PDO1_PORTB = 0x1F84F  # POrt 0 - start of 7*32-bit PDOs

    # Src PDOs
    SRC_PDO_COUNT_PORTA = 0x1F811  # Port 1
    SRC_PDO_COUNT_PORTB = 0x1F810  # Port 0
    SRC_PDO_OFFSET_PDO1_PORTA = 0x1F82E  # Port 1 - start of 7*32-bit PDOs
    SRC_PDO_OFFSET_PDO1_PORTB = 0x1F812  # POrt 0 - start of 7*32-bit PDOs

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


class RtkDebugAccyGpioPolarity(enum.IntEnum):
    """Debug accessory detect GPIO polarity

    Indicates the polarity of the GPIO toggled in response to USB-C
    debug accessory mode being entered. Used to control CCD entry.
    """

    ACTIVE_LOW = 0x00
    ACTIVE_HIGH = 0x01
    DISABLED = 0xFF


class RtkI2cBusVoltage(enum.IntEnum):
    """Voltage level used on the PDC I2C interfaces (SMBus/EC, PMC, Retimer)"""

    LEVEL_1V8 = 0
    LEVEL_3V3 = 1

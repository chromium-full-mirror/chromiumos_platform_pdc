# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common classes for use with the EC console-based PDC updater"""

import ast
import dataclasses
import logging
from typing import List, Optional, Tuple
import xmlrpc.client


@dataclasses.dataclass
class ChipSpec:
    """Base class for methods of specifying a PDC chip to update"""

    @property
    def is_port_num_known(self):
        """True if the port number of the PDC target is known"""
        return isinstance(self, ChipSpecPortNum)


@dataclasses.dataclass
class ChipSpecPortNum(ChipSpec):
    """Specify a PDC chip by USB-C port number"""

    port_number: int

    def __str__(self):
        return f"Port C{self.port_number}"


@dataclasses.dataclass
class ChipSpecRawI2C(ChipSpec):
    """Specify a PDC chip by raw I2C bus name and address"""

    i2c_bus: str
    i2c_addr: int

    def __str__(self):
        return f"I2C {self.i2c_bus}:{self.i2c_addr}"


class ServodClient(xmlrpc.client.ServerProxy):
    """Interface with `servod` using the HTTP XML RPC interface

    This is significantly faster than calling dut-control as a subprocess since
    we don't need to start up a docker container each time. Programming the PDC
    requires several thousand console commands to be issued.
    """

    # Servod control names
    CONTROL_EC_UART_REGEXP = "ec_uart_regexp"
    CONTROL_EC_UART_CMD = "ec_uart_cmd"
    CONTROL_EC_UART_TIMEOUT = "ec_uart_timeout"

    def __init__(self, servod_host: str, servod_port: int):
        uri = f"http://{servod_host}:{servod_port}"

        super().__init__(uri)

        self.log = logging.getLogger()
        self.log.info("Connecting to servod at %s", uri)

    def _run_ec_command_get_output(
        self, cmd: str, regexp: List[str]
    ) -> List[str]:
        """Run an EC console command and return output matching the regexp"""

        if not regexp:
            raise ValueError("Need regular expressions to match on")

        try:
            # Servod expects the (escaped) string representation of a Python
            # list
            self.set(ServodClient.CONTROL_EC_UART_REGEXP, str(regexp))

            self.set(ServodClient.CONTROL_EC_UART_CMD, cmd)

            return ast.literal_eval(self.get(ServodClient.CONTROL_EC_UART_CMD))
        finally:
            self.set(ServodClient.CONTROL_EC_UART_REGEXP, "None")

    def _run_ec_command(self, cmd: str) -> None:
        """Run an EC command but don't collect any output"""
        self.set(ServodClient.CONTROL_EC_UART_CMD, cmd)

    def get_ec_console_pdc_fw_ver(
        self, port: int, live: Optional[bool] = True
    ) -> Tuple[Tuple[int, int, int], str]:
        """Get the current PDC FW version and project name via EC console"""

        output = self._run_ec_command_get_output(
            f"pdc info {port} {int(live)}",
            [
                "FW Ver: ([\\d]+).([\\d]+).([\\d]+)\r\n",
                "Project Name: '(.*)'\r\n",
            ],
        )

        # Return a ((major, minor, patch), project name) tuple
        return (
            (int(output[0][1]), int(output[0][2]), int(output[0][3])),
            output[1][1],
        )

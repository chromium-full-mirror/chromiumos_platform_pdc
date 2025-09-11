# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Implements the EC-console-based PDC updater for RTK chips"""

import base64
import logging
from pathlib import Path
import struct
import time
from typing import Tuple
import xmlrpc.client

from pdclib import console_fwup_common
from pdclib import rtk_constants
from pdclib import rtk_utils


# Number of host FWUP packets to send at a time, per call to
# `pdc_rtk_fwup write`. This is impacted by the Zephyr shell buffer size.
# Overrunning this buffer on the EC console side will result in loss of data.
HOST_FWUP_PACKET_MAX_CHUNK_COUNT = 2

# Maximum number of FW payload bytes that can be included in each write packet,
# per the RTK ISP interface
RTK_FW_CHUNK_SIZE = 29

# Struct definition must match the EC's `struct host_fwup_packet` in
# `zephyr/drivers/usbc/pdc_rts54xx_fwup.c`
HOST_FWUP_PACKET_FMT = "<BHB29s"
assert struct.calcsize(HOST_FWUP_PACKET_FMT) == 33


class RtkUpdaterServodClient(console_fwup_common.ServodClient):
    """Provide RTK-specific implementations of the EC console command API"""

    def fwup_start(self, chip: console_fwup_common.ChipSpec):
        """Start a FW update session"""

        if isinstance(chip, console_fwup_common.ChipSpecPortNum):
            self._run_ec_command_get_output(
                f"pdc_rtk_fwup start {chip.port_number}", ["RTK_FWUP: Started"]
            )
        elif isinstance(chip, console_fwup_common.ChipSpecRawI2C):
            self._run_ec_command_get_output(
                f"pdc_rtk_fwup start {chip.i2c_bus} {chip.i2c_addr}",
                ["RTK_FWUP: Started"],
            )
        else:
            raise RuntimeError(f"Invalid chip spec type {chip}")

    def fwup_write(self, data: bytes) -> int:
        """Transfer FW payload data to the EC via the console"""

        cmd = f"pdc_rtk_fwup write {base64.b64encode(data).decode('ascii')}"

        output = self._run_ec_command_get_output(
            cmd, ["RTK_FWUP: bytes written: (\\d+)\r\n"]
        )

        return int(output[0][1])

    def fwup_finish(self):
        """Finalize the update after all data is transferred"""

        orig_timeout = self.get(RtkUpdaterServodClient.CONTROL_EC_UART_TIMEOUT)

        # Extend the UART timeout because the validation and restart delay
        # steps take a long time (~7s + 5s)
        self.set(RtkUpdaterServodClient.CONTROL_EC_UART_TIMEOUT, 16.0)
        try:
            self._run_ec_command_get_output(
                "pdc_rtk_fwup finish", ["PDC FWUP successful"]
            )
        finally:
            self.set(
                RtkUpdaterServodClient.CONTROL_EC_UART_TIMEOUT, orig_timeout
            )

    def fwup_abort(self):
        """Try to recover the PDC subsystem after a failed update procedure"""

        self._run_ec_command("pdc_rtk_fwup abort")


def _stream_firmware(
    fw: rtk_utils.RtkFwBinary, servo: console_fwup_common.ServodClient
):
    """Write the supplied PDC FW binary to the EC console piece by piece"""

    log = logging.getLogger()

    bytes_written = 0
    ec_bytes_received = 0

    progress_log_target = 4000

    log.info("Starting FW transfer")

    def get_next_chunk() -> Tuple[int, bytes]:
        # Return the next firmware chunk up to 29 bytes at a time. Write cannot
        # cross a flash segment boundary (64 KiB, 128 KiB)

        segment = (
            0 if bytes_written < rtk_constants.RtkFwOffset.SEGMENT_SIZE else 1
        )
        segment_boundary = rtk_constants.RtkFwOffset.SEGMENT_SIZE * (
            segment + 1
        )
        chunk_len = min(
            RTK_FW_CHUNK_SIZE,
            min(segment_boundary, fw.get_size()) - bytes_written,
        )

        return segment, fw.get_range(bytes_written, chunk_len)

    while bytes_written < fw.get_size():
        packets = bytearray()

        for _ in range(HOST_FWUP_PACKET_MAX_CHUNK_COUNT):
            # Line up as many packets as possible. Sending multiple in one
            # console command invocation reduces overhead.
            seg, chunk = get_next_chunk()

            if len(chunk) == 0:
                # All done
                break

            # Build packet and append to the buffer for transmission
            packets.extend(
                struct.pack(
                    HOST_FWUP_PACKET_FMT,
                    seg,
                    bytes_written & 0xFFFF,
                    len(chunk),
                    chunk.ljust(RTK_FW_CHUNK_SIZE, b"\x00"),
                )
            )
            log.debug(
                "Packet: seg=%d, offset=%d, len=%d",
                seg,
                bytes_written & 0xFFFF,
                len(chunk),
            )

            bytes_written += len(chunk)

        log.debug(
            "Transmit: len=%d (%d packets), bytes_written=%d",
            len(packets),
            len(packets) / struct.calcsize(HOST_FWUP_PACKET_FMT),
            bytes_written,
        )

        # Send to console
        ec_bytes_received = servo.fwup_write(packets)

        assert (
            ec_bytes_received == bytes_written
        ), f"{ec_bytes_received=} vs {bytes_written=}"

        # Show progress info every 4KB transferred
        if ec_bytes_received > progress_log_target:
            log.info(
                "Progess: %d/%d bytes transferred (%.2f%%)",
                progress_log_target,
                rtk_constants.RtkFwOffset.TOTAL_SIZE,
                100.0
                * progress_log_target
                / rtk_constants.RtkFwOffset.TOTAL_SIZE,
            )
            progress_log_target += 4000

    log.info(
        "FW transfer completed: %d/%d bytes received by EC",
        ec_bytes_received,
        rtk_constants.RtkFwOffset.TOTAL_SIZE,
    )


def rtk_update(
    servod_host: str,
    servod_port: int,
    pdc_fw_path: Path,
    chip: console_fwup_common.ChipSpec,
) -> int:
    """Process a RTK PDC FW update"""

    log = logging.getLogger()

    fw = rtk_utils.RtkFwBinary(pdc_fw_path)

    assert fw.verify_crc32(), "The CRC32 of the provided FW binary is incorrect"

    log.info(
        "New FW: %s ('%s'), %s, Port Config: %s",
        fw.get_fw_version(),
        fw.get_project_name(),
        fw.get_vid_pid(),
        fw.get_port_used().name,
    )

    servo = RtkUpdaterServodClient(servod_host, servod_port)

    if chip.is_port_num_known:
        # This is only supported if a port number is passed. Skip for raw I2C
        # updates.
        try:
            pdc_live_ver, pdc_live_proj_name = servo.get_ec_console_pdc_fw_ver(
                chip.port_number
            )
            log.info(
                "Current FW: %d.%d.%d ('%s')", *pdc_live_ver, pdc_live_proj_name
            )
        except xmlrpc.client.Fault:
            log.warning(
                "Cannot read current FW (pdc info). Proceeding anyways."
            )

    try:
        # Start firmware update session
        log.info("Starting firmware update session (%s)", chip)
        servo.fwup_start(chip)

        # Stream FW through the console
        _stream_firmware(fw, servo)

        # Finish firmware update session
        log.info("Finalizing firmware update. This may take a moment.")
        servo.fwup_finish()
        log.info("✅ Update succeeded")
    except:
        # In case of failure, try to recover the PDC subsystem
        log.info("❌ Update failed. Attempting to recover PDC.")

        servo.fwup_abort()
        raise

    # Check FW version again after update. Using a polling routine because the
    # PDC stack might still be re-initializing immediately after finishing the
    # update.
    if chip.is_port_num_known:
        # This is only supported if a port number is passed. Skip for raw I2C
        # updates.
        for _ in range(3):
            time.sleep(2.0)
            try:
                pdc_live_ver, pdc_live_proj_name = servo.get_pdc_fw_ver(
                    chip.port_number
                )
                log.info(
                    "Current FW: %d.%d.%d ('%s')",
                    *pdc_live_ver,
                    pdc_live_proj_name,
                )
                break
            except xmlrpc.client.Fault:
                log.info("Waiting for PDC stack to restart...")

    return 0

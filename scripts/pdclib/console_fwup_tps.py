# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Implements the EC-console-based PDC updater for TPS chips"""

import base64
import logging
from pathlib import Path
import struct

from pdclib import console_fwup_common


class TpsUpdaterServodClient(console_fwup_common.ServodClient):
    """Provide TPS-specific implementations of the EC console command API"""

    def fwup_start(self, port: int):
        """Start a FW update session"""

        self._run_ec_command_get_output(
            f"pdc_tps_fwup start {port}", ["TPS_FWUP: Started"]
        )

    def fwup_initiate(self, data: bytes):
        """Send initiate command via TFU"""
        cmd = (
            "pdc_tps_fwup send_initiate "
            f"{base64.b64encode(data).decode('ascii')}"
        )
        self._run_ec_command_get_output(
            cmd, ["TPS_FWUP: Send Initiate complete"]
        )

    def fwup_block(self, data: bytes):
        """Send block command via TFU"""
        cmd = (
            f"pdc_tps_fwup send_block {base64.b64encode(data).decode('ascii')}"
        )
        self._run_ec_command_get_output(cmd, ["TPS_FWUP: Send Block complete"])

    def fwup_stream(self, broadcast_address: int, data: bytes) -> int:
        """Transfer FW payload data to the EC via the console"""

        broadcast_bytes = struct.pack("<H", broadcast_address)
        buf = broadcast_bytes + data

        cmd = f"pdc_tps_fwup stream {base64.b64encode(buf).decode('ascii')}"
        output = self._run_ec_command_get_output(
            cmd, ["TPS_FWUP: Stream - bytes written: (\\d+)\r\n"]
        )

        return int(output[0][1])

    def fwup_complete(self):
        """Finalize the update after all data is transferred"""

        orig_timeout = self.get(TpsUpdaterServodClient.CONTROL_EC_UART_TIMEOUT)

        # Extend the UART timeout because the validation and restart delay
        # steps take a long time (~7s + 5s)
        self.set(TpsUpdaterServodClient.CONTROL_EC_UART_TIMEOUT, 16.0)
        try:
            self._run_ec_command_get_output(
                "pdc_tps_fwup complete", ["PDC FWUP successful"]
            )
        finally:
            self.set(
                TpsUpdaterServodClient.CONTROL_EC_UART_TIMEOUT, orig_timeout
            )

    def fwup_abort(self):
        """Try to recover the PDC subsystem after a failed update procedure"""

        self._run_ec_command("pdc_tps_fwup abort")


class TfuiData:
    """Unpacked data for TFUi"""

    def __init__(self, data: bytes):
        (
            self.num_blocks,
            self.data_block_size,
            self.timeout_secs,
            self.broadcast_address,
        ) = struct.unpack("<HHHH", data)


class TfudData:
    """Unpacked data for TFUd"""

    def __init__(self, data: bytes):
        (
            self.num_blocks,
            self.data_block_size,
            self.timeout_secs,
            self.broadcast_address,
        ) = struct.unpack("<HHHH", data)


class Tps6699xFirmwareUpdater:
    """Firmware updater for TPS6699x PDC."""

    MAX_READ_CHUNK_SIZE = 0x4000

    # TFUI file constants
    TFUI_METADATA_OFFSET = 0x4
    TFUI_METADATA_LENGTH = 0x8
    TFUI_STREAM_HEADER_BLOCK_OFFSET = 0xC
    TFUI_STREAM_HEADER_BLOCK_LENGTH = 0x800

    # TFUD file constants
    TFUD_REGION_OFFSET = 0x80C
    TFUD_BLOCK_SIZE = 0x4000
    TFUD_METADATA_LENGTH = 0x8
    TFUD_CHUNK_SIZE = 64
    TFUD_MAX_NUM_BLOCKS = 12

    # Size of fw not including appconfig and header block is at this offset. */
    FW_SIZE_OFFSET = 0x4F8

    # Streaming packets will be the broadcast byte + 64 bytes of string data
    HOST_STREAM_PACKET_FMT = "<B64s"
    STREAM_SIZE = 64

    def __init__(self, servo: TpsUpdaterServodClient):
        self.servo = servo

    def _TFUD_METADATA_OFFSET_AT(self, block: int) -> int:
        return (
            (self.TFUD_BLOCK_SIZE + self.TFUD_METADATA_LENGTH) * block
        ) + self.TFUD_REGION_OFFSET

    def _TFUD_DATA_AT(self, block: int) -> int:
        return self._TFUD_METADATA_OFFSET_AT(block) + self.TFUD_METADATA_LENGTH

    def _APPCONFIG_DATA(self, fw_size: int, num_data_blocks: int) -> (int, int):
        # The Application Configuration is stored at the following offset:
        # FirmwareImageSize (Which excludes Header and App Config)
        #   + 0x800 (Header Block Size)
        #   + (8 (Meta Data for Each Block + header) * Number of Data block + 1)
        #   + 4 (File Identifier)
        metadata_offset = (
            fw_size
            + self.TFUI_STREAM_HEADER_BLOCK_LENGTH
            + (self.TFUD_METADATA_LENGTH * (num_data_blocks + 1))
            + 4
        )

        # Appconfig block uses same metadata block as TFUd so data is after the
        # metadata.
        data_block_offset = metadata_offset + self.TFUD_METADATA_LENGTH

        return (metadata_offset, data_block_offset)

    def _read_data(self, data: bytes, offset: int, length: int) -> bytes:
        return data[offset : offset + length]

    def update(self, usbc_port: int, fw_image: bytes):
        """Update firmware with the supplied PDC FW binary."""

        def chunk_stream(stream_for, broadcast_address, buf):
            """Chunk a single stream into multiple calls to the EC."""
            buf_len = len(buf)
            count = (buf_len // self.STREAM_SIZE) + 1
            ec_bytes_received = 0
            bytes_written = 0
            progress_log_target = 4000

            for _ in range(count):
                (start, end) = (
                    bytes_written,
                    min(bytes_written + self.STREAM_SIZE, buf_len),
                )
                # Send to console
                ec_bytes_received = self.servo.fwup_stream(
                    broadcast_address, buf[start:end]
                )

                assert (
                    ec_bytes_received == end
                ), f"{ec_bytes_received=} vs {end=}"

                bytes_written = end

                # Show progress info every 4KB transferred
                if ec_bytes_received > progress_log_target:
                    log.info(
                        "%s: Progess: %d/%d bytes transferred (%.2f%%)",
                        stream_for,
                        progress_log_target,
                        buf_len,
                        100.0 * progress_log_target / buf_len,
                    )
                    progress_log_target += 4000

        def do_tfud_block(msg_prefix, metadata_offset, data_offset):
            """Handle a single TFUd block + stream."""
            tfud_buf = self._read_data(
                fw_image, metadata_offset, self.TFUD_METADATA_LENGTH
            )
            tfud = TfudData(tfud_buf)
            stream_data = self._read_data(
                fw_image, data_offset, tfud.data_block_size
            )
            self.servo.fwup_block(tfud_buf)
            chunk_stream(msg_prefix, tfud.broadcast_address, stream_data)

        log = logging.getLogger()

        try:
            # Start firmware update session
            log.info("Starting firmware update session (port C%d)", usbc_port)
            self.servo.fwup_start(usbc_port)

            log.info("Sending data blocks")
            # Send TFUi command and then stream the header
            tfui_buf = self._read_data(
                fw_image, self.TFUI_METADATA_OFFSET, self.TFUI_METADATA_LENGTH
            )
            tfui_header = self._read_data(
                fw_image,
                self.TFUI_STREAM_HEADER_BLOCK_OFFSET,
                self.TFUI_STREAM_HEADER_BLOCK_LENGTH,
            )
            tfui = TfuiData(tfui_buf)
            self.servo.fwup_initiate(tfui_buf)
            chunk_stream("FW header", tfui.broadcast_address, tfui_header)

            # TFUd will enumerate blocks
            for block in range(tfui.num_blocks):
                do_tfud_block(
                    f"Block{block}",
                    self._TFUD_METADATA_OFFSET_AT(block),
                    self._TFUD_DATA_AT(block),
                )

            log.info("Sending appconfig")
            # Last, do the appconfig region.
            fw_size_buf = self._read_data(fw_image, self.FW_SIZE_OFFSET, 4)
            (fw_size,) = struct.unpack("<I", fw_size_buf)

            (metadata_offset, stream_data_offset) = self._APPCONFIG_DATA(
                fw_size, tfui.num_blocks
            )
            do_tfud_block("Appconfig", metadata_offset, stream_data_offset)

            # Complete firmware update session
            log.info("Finalizing firmware update. This may take a moment.")
            self.servo.fwup_complete()
            log.info("✅ Update succeeded")
        except:
            # In case of failure, try to recover the PDC subsystem
            log.info("❌ Update failed. Attempting to recover PDC.")

            self.servo.fwup_abort()
            raise


def tps_update(
    servod_host: str,
    servod_port: int,
    pdc_fw_path: Path,
    chip: console_fwup_common.ChipSpec,
) -> int:

    servo = TpsUpdaterServodClient(servod_host, servod_port)
    tps = Tps6699xFirmwareUpdater(servo)

    if not chip.is_port_num_known:
        raise Exception(f"TPS update only supports port numbers: {chip}")

    with open(pdc_fw_path, "rb") as f:
        pdc_fw = f.read()

    tps.update(chip.port_number, pdc_fw)

    return 0

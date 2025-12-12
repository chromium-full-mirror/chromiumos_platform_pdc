# EC Console-based PDC Firmware Updates

**Purpose:** Provide a fast mechanism for engineers to update the PDC without
needing special cables or having to compile AP or EC FW images.

**Status:** Realtek and TI PDCs supported

**Code links:**
  * EC firmware: [pdc_rts54xx_fwup.c](https://chromium.googlesource.com/chromiumos/platform/ec/+/refs/heads/main/zephyr/drivers/usbc/pdc_rts54xx_fwup.c),
    [tps6699x_fwup.c](https://chromium.googlesource.com/chromiumos/platform/ec/+/refs/heads/main/zephyr/drivers/usbc/tps6699x_fwup.c)
  * Host script: [pdc_console_fwup.py](../scripts/pdc_console_fwup.py)

## Background
Our standard PDC FW update mechanism uses the auxiliary firmware sync feature
of Depthcharge to reflash the PDCs. ([RTK](https://chromium.googlesource.com/chromiumos/platform/depthcharge/+/refs/heads/main/src/drivers/ec/rts5453/),
[TI](https://chromium.googlesource.com/chromiumos/platform/depthcharge/+/refs/heads/main/src/drivers/ec/tps6699x/))
This is the process that devices in the field use for updating the PDC.
However, for engineering and testing purposes, having to recompile and/or
reflash an AP FW image to change the PDC FW is very tedious and can easily take
half an hour.

## Solution
EC console-based PDC update solves these challenges and is fast and flexible.
No PDC FW image needs to be bundled into either AP or EC FW. Instead, the new
PDC FW payload is streamed by a Python script running on the host, through the
EC’s serial console interface, and to the PDC. The transfer takes 3.5 minutes.

## How to Use

### Prerequisites
  * The EC firmware must have the Kconfig option
    `CONFIG_USBC_PDC_RTS54XX_CONSOLE_FW_UPDATER` and/or
    `CONFIG_USBC_PDC_TPS6699X_CONSOLE_FW_UPDATER` enabled. This option depends
    on `CONFIG_PLATFORM_EC_SYSTEM_UNLOCKED`, which is typically only enabled
    during the bringup phase for security reasons. You can determine if EC
    support is present by seeing if the `pdc_rtk_fwup` and/or `pdc_tps_fwup`
    EC console command is present.
  * You must be running [`servod`](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/HEAD/docs/servod_outside_chroot.md)
    and have any Servo or Suzy Qable attached for EC console access. Make sure
    you add `-p 9999` to `start-servod` to expose the port for remote command
    access.

### Warnings
  * The console PDC updater does not verify compatibility of the incoming FW
    image. It will attempt to flash whatever image the user provides. Only the
    currently-running PDC FW validates the newly received image based on
    whatever checks are present on the current firmware (CRC, signature
    verification, project name check, or anti-rollback enforcement). Flashing
    improper FW can damage the system, prevent booting, or prevent charging.
  * If testing new PDC FW, ensure that the GBB flag
    `VB2_GBB_FLAG_DISABLE_AUXFW_SOFTWARE_SYNC` is set to prevent Depthcharge
    from reverting your PDC FW back to its bundled version upon the next reboot.
    Note that FAFT/TAST may deactivate this flag when running tests, in which
    case, the PDC might get overwritten again to the bundled version.

### Transfer Firmware
On the host machine, run the Python script
`platform/pdc/scripts/pdc_console_fwup.py`. You do not need to be in the chroot.

Make sure to specify `--pdc_driver rtk` or `--pdc_driver tps`.

```bash
~/chromiumos/src/platform/pdc$ scripts/pdc_console_fwup.py --pdc_driver [rtk|tps] ~/Downloads/pdc_firmware.bin

2025-04-09 16:09:14 INFO     New FW: 16.0.1 ('GOOG0000'), 18d1:5065, Port Config: Dual-port
2025-04-09 16:09:14 INFO     Connecting to servod at http://localhost:9999
2025-04-09 16:09:14 INFO     Current FW: 16.0.1 ('GOOG0000')
2025-04-09 16:09:14 INFO     Starting firmware update session (port C0)
2025-04-09 16:09:14 INFO     Starting FW transfer
2025-04-09 16:09:21 INFO     Progess: 4000/131072 bytes transferred (3.05%)
2025-04-09 16:09:27 INFO     Progess: 8000/131072 bytes transferred (6.10%)
[...]
2025-04-09 16:12:24 INFO     Progess: 124000/131072 bytes transferred (94.60%)
2025-04-09 16:12:30 INFO     Progess: 128000/131072 bytes transferred (97.66%)
2025-04-09 16:12:35 INFO     FW transfer completed: 131072/131072 bytes received by EC
2025-04-09 16:12:35 INFO     Finalizing firmware update. This may take a moment.
2025-04-09 16:12:48 INFO     ✅ Update succeeded
2025-04-09 16:12:51 INFO     Current FW: 16.0.1 ('GOOG0000')
```

The script connects to `servod` and issues console commands to reprogram the
PDC. Additional CLI args are supported:

  * `-c` / `--usbc_port` - Send the update to the specified port number. This
    is needed in systems with multiple PDC chips. Default is 0 for port C0.
  * `--i2c_target` - Advanced feature to specify a specific I2C bus and target
    I2C address (I2C_PORT_PD:0x66). Used instead of `--usbc_port`.
  * `--host`, `--port` - Override the `servod` host and port. Default is
    `localhost:9999`

### Troubleshooting
If the PDC update fails and is interrupted, you should simply be able to try
again. If you encounter errors, try manually issuing the `pdc_rtk_fwup abort`
console command in the EC to reset some system state. Because the PDC has dual
flash banks, and only one is updated at a time, a failed update should not
corrupt the PDC.

Sometimes a failure is reported mistakenly when excessive EC console logging
clobbers the output of a command, causing `servod` to not match an expected
string in the output. If this happens during the final stage (Finalizing
update), the error is likely benign and the update did actually finish.
Run `pdc info <port>` in the EC console to see if the new PDC FW version is
running. Otherwise, try turning off all but the Zephyr logs with:
`chan 0` then `chan zephyr_logs` and retrying.

The script is calling the following console commands behind the scenes. You
should not need to interact with these, but they are described below:

  * `pdc_rtk_fwup start <port>`
    * Initiate a PDC FW update session, targeting the specified port. The port
      number is cached for the remaining command calls. This command suspends
      the PDC subsystem (all ports, the equivalent of pdc comms suspend) and
      issues commands to the PDC to enter flash programming mode. See the
      Realtek ISP manual for more details.
  * `pdc_rtk_fwup write <payload>`
    * Steam a piece of FW payload data to the EC. The payload is Base64-encoded
      to permit transfer through the text-based console interface. The payload
      consists of a series of struct host_fwup_packet packets (see
      `zephyr/drivers/usbc/pdc_rts54xx_fwup.c`) that each contain: (1) flash
      segment identifier (lower or upper 64KiB), (2) an offset within the flash
      segment to start writing at, (3) a length, and (4) a fixed-size 29-byte
      buffer for FW data. Each Host FWUP Packet is 33 bytes long. The current
      implementation transfers 2 of these packets at a time, limited by the size
      of the EC’s shell input buffer. The contents of each packet map directly
      to flash write commands sent to the PDC.
  * `pdc_rtk_fwup finish`
    * Validate the update, and if successful, reboot the PDC so it switches over
      to the freshly flashed image. Restarts the PDC subsystem (equivalent of
      `pdc comms resume`) after a waiting period.

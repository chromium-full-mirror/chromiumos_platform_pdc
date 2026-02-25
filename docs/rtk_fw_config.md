# Realtek Firmware Configuration Tool (`rtk_fw_config.py`)

The `rtk_fw_config.py` script is a command-line tool used to manage the
configuration data within a Realtek Power Delivery Controller (PDC) firmware
binary. It allows you to display, extract, or update the configuration block
embedded in the firmware.

This is particularly useful when you need to:
- Inspect the current settings of a firmware file.
- Create a new firmware variant by applying a customized configuration to a base
  firmware image.
- Extract a configuration from an existing firmware to use as a baseline for a
  new board or product.

## Usage

The script is located in the `scripts/` directory. It uses [vpython] to
automatically set up dependencies. It can be run inside or outside of the
chroot.

### Displaying Current Configuration (`show`)

To view the vital configuration parameters of a firmware binary or config
fragment, provide the path to the file as the main argument. This will print a
summary of the configuration without modifying the file.

**Command:**
```bash
./scripts/rtk_fw_config.py show -i <path/to/firmware-or-config.bin>
```

**Example:**
```bash
# Full FW image
./scripts/rtk_fw_config.py show -i firmware/realtek/rts5453/rts5453_v16.2.3.bin

# Config fragment
./scripts/rtk_fw_config.py show -i program/ocelot/ocelotrvp/ocelotrvp-GOOG0H00-config.bin
```

This will produce output detailing the Customer ID, version, checksum, and other
important values from the firmware's configuration block.

### Extracting a Configuration File (`extract`)

You can extract the configuration block from a firmware binary and save it to a
new file. This is useful for backup purposes or for using it as a template for a
new configuration.

**Command:**
```bash
./scripts/rtk_fw_config.py extract \
    -i <path/to/firmware.bin> \
    -o <path/to/save/config.bin>
```

**Example:**
```bash
./scripts/rtk_fw_config.py extract \
    -i firmware/realtek/rts5453/rts5453_v16.2.3.bin \
    -o my_config.bin
```

This command reads the firmware, extracts the configuration, and saves it to
`my_config.bin`.

### Patching a New Configuration (`merge`)

This is the primary function for creating new firmware images. It takes a base
firmware binary and a separate configuration file, and produces a new firmware
binary with the configuration patched in. The script automatically recalculates
the necessary checksums to ensure the resulting firmware is valid.

To perform this action, you must provide the input firmware, the new
configuration file, and a path for the output file.

The config format version of the base firmware binary and the configuration file
must match. The last digit of the firmware release number denotes the config
format version.

* [rts5453_v0.44.3.bin] - This base firmware uses config format version v3.
* [rts5453_v0.45.4.bin] - This base firmware uses config format version v4.


**Command:**
```bash
./scripts/rtk_fw_config.py merge \
    -i <path/to/base_firmware.bin> \
    -c <path/to/new_config.bin> \
    -o <path/to/new_firmware.bin>
```

**Example:**
```bash
./scripts/rtk_fw_config.py merge \
    -i firmware/realtek/rts5453/rts5453_v16.2.3.bin \
    -c program/skywalker/grogu/grogu-GOOG0E00-config.bin \
    -o grogu-firmware.bin
```

This will create `grogu-firmware.bin`, which is a copy of `rts5453_v16.2.3.bin`
but with the configuration from `grogu-GOOG0E00-config.bin` applied.

## Command-Line Arguments

Run `./rtk_fw_config.py -h` for a listing of supported subcommands, and
`./rtk_fw_config.py <subcommand> -h` for help with a particular subcommand.

[rts5453_v0.44.3.bin]: ../firmware/realtek/rts5453/rts5453_v0.44.3.bin
[rts5453_v0.45.4.bin]: ../firmware/realtek/rts5453/rts5453_v0.45.4.bin
[vpython]: https://chromium.googlesource.com/infra/infra/+/HEAD/doc/users/vpython.md

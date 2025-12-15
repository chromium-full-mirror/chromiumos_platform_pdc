# PDC Configuration Fragment Files

The [`./program`](../program) directory under the platform/pdc repository is
used to store PDC configuration fragment files.

The directory is organized using the same definitions of **program** and
**project** used by the boxster configuration system.

## Directory structure

Each **program** has it's own subdirectory under `./program`.

```
./program/brox
./program/fatcat
./program/ocelot
...
```

Each **program** directory contains a subdirectory for each **project**.

```
program/
├── brox
│   ├── brox
│   │   ├── brox-GOOG0000-config.bin
│   │   └── brox-GOOG0100-config.bin
│   └── caboc
│       └── caboc-GOOG0L01-config.bin
├── fatcat
│   ├── francka
│   │   ├── francka-GOOG0500-config.bin
│   │   └── francka-GOOG0A20-appconfig.json
│   └── ruby
│       └── ruby_GOOG0P00-config.bin
├── ocelot
│   ├── kodkod
│   │   └── kodkod-GOOG0T00-config.bin
│   ├── ocelotrvp
│   │   ├── ocelotrvp-GOOG0H00-config.bin
│   │   ├── ocelotrvp_tps66990-GOOG0J20-appconfig.json
│   │   ├── ocelotrvp_tps66993-GOOG0I00-appconfig.json
│   │   └── ocelotrvp_tps66993-GOOG0I01-appconfig.json
│   └── ocicat
│       └── ocicat-GOOG0L02-config.bin
...
```

## PDC firmware filename conventions

To make PDC firmware files parsable by humans, the following conventions are
used:

* Realtek format: `<project>-<pdc_config_id>-<chip_type>-config.bin`
* TI format: `<project>-<pdc_config_id>-<chip_type>-appconfig.json`

The components of the filename are:

* `<project>` - This should match the **project** name, lowercase.
* `<pdc_config_id>` - The 8-byte project PDC configuration identifier. Always
starts with "GOOG" as defined in the [PDC Config ID](#pdc-config-id) section.
* `<chip_type>` - The PDC chip type, lowercase.

## PDC Config ID
The PDC Config ID is an 8-byte identifier, assigned by Google, consisting of the
following parts:

| Byte(s) | Description |
|---|---|
| 0-3 | Fixed to the string "GOOG". |
| 4-5 | 2 character configuration identifier. This identifier is unique across all program and projects. |
| 6 | Single character configuration revision. Unique within the same configuration identifier. Increments for each revision. |
| 7 | Single character variant identifier. Unique within the same configuration identifier. |

The configuration identifier, configuration version, and variant identifier all
increment character using the ASCII byte code order (0-9, A-Z, a-z). No special
characters are permitted.

The variant identifier is used to differentiate items including, but not limited to:

* VID/PID for a different platform with the same PDC assembly.
* AUX orientation based on the HW topology.
* EQ tuning.

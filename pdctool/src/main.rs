// Copyright 2026 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use clap::{Parser, Subcommand};

const RTK_TOTAL_SIZE: usize = 2 * 64 * 1024;
const RTK_CONFIG_START: usize = 0x1F800;
const RTK_CONFIG_END: usize = 0x1FC60;
const RTK_CONFIG_LEN: usize = RTK_CONFIG_END - RTK_CONFIG_START;
const RTK_FW_VER_MAJOR: usize = 0x7EF9;
const RTK_FW_VER_MINOR: usize = 0x7EFA;
const RTK_CFG_VER_OFFSET: usize = 0x02;
const RTK_PROJ_NAME_OFFSET: usize = 0x400;
const RTK_PROJ_NAME_LEN: usize = 12;
const RTK_CRC_END: usize = 0x1FFE6;

const TI_TFU_TYPE_A: [u8; 4] = [0x03, 0x00, 0xEF, 0xAC];
const TI_TFU_TYPE_B: [u8; 4] = [0x13, 0x00, 0xEF, 0xAC];
const TI_APPCONFIG: [u8; 4] = [0x03, 0x00, 0xEA, 0xAC];
const TI_NUM_BLOCKS_OFFSET: usize = 0x04;
const TI_FWVER_OFFSET: usize = 0x4F4;
const TI_FW_SIZE_OFFSET: usize = 0x4F8;
const TI_HEADER_BLOCK_LEN: usize = 0x800;
const TI_DATA_METADATA_LEN: usize = 0x08;
const TI_METADATA_OFFSET: usize = 0x04;
const TI_PROJ_NAME_OFFSET: usize = 30;
const TI_PROJ_NAME_LEN: usize = 8;

#[derive(Parser)]
#[command(name = "pdctool", about = "PDC firmware version and hash utility")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Generate a PDC .hash file or write hash bytes to stdout
    Hash {
        /// Path to PDC firmware image
        image: PathBuf,
        /// Output path for the generated .hash file (writes to stdout if omitted)
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
    /// Report PDC firmware version and project name
    Version {
        /// Path to PDC firmware image
        image: PathBuf,
    },
}

#[derive(Debug, PartialEq, Eq)]
pub enum PdcImageInfo {
    Ti {
        ver: Option<(u8, u8, u8)>,
        proj_name: Option<String>,
        raw_proj: Option<[u8; TI_PROJ_NAME_LEN]>,
    },
    RtkFw {
        ver: (u8, u8, u8),
        proj_name: Option<String>,
    },
    RtkCfg {
        cfg_ver: u8,
        proj_name: Option<String>,
    },
}

fn rtk_crc32(data: &[u8]) -> u32 {
    let mut crc = 0xFFFF_FFFFu32;
    for &b in data {
        crc ^= u32::from(b);
        for _ in 0..8 {
            crc = if crc & 1 != 0 {
                (crc >> 1) ^ 0xEDB8_8320
            } else {
                crc >> 1
            };
        }
    }
    crc
}

fn rtk_proj_name(cfg: &[u8]) -> Option<String> {
    let raw = cfg.get(RTK_PROJ_NAME_OFFSET..RTK_PROJ_NAME_OFFSET + RTK_PROJ_NAME_LEN)?;
    if !raw.iter().all(|&b| b.is_ascii()) {
        return None;
    }
    let s = std::str::from_utf8(raw)
        .ok()?
        .trim_matches('\0')
        .to_string();
    Some(s)
}

fn format_ti_proj_name(raw: &[u8; TI_PROJ_NAME_LEN]) -> String {
    if raw.starts_with(b"GOOG") {
        raw.iter()
            .map(|&b| {
                if b.is_ascii() && b != 0 {
                    b as char
                } else {
                    '?'
                }
            })
            .collect()
    } else {
        let mut s = String::from("0x");
        for &b in raw {
            s.push_str(&format!("{b:02x}"));
        }
        s
    }
}

pub fn parse_pdc_image(data: &[u8]) -> Result<PdcImageInfo, String> {
    if let Some(hdr) = data.get(0..4) {
        if hdr == TI_TFU_TYPE_A || hdr == TI_TFU_TYPE_B {
            if data.len() < TI_FW_SIZE_OFFSET + 4 {
                return Err("TI PDC binary is too short to read metadata".into());
            }
            let patch = data[TI_FWVER_OFFSET];
            let minor = data[TI_FWVER_OFFSET + 1];
            let major = data[TI_FWVER_OFFSET + 2];
            let num_blocks = usize::from(u16::from_le_bytes([
                data[TI_NUM_BLOCKS_OFFSET],
                data[TI_NUM_BLOCKS_OFFSET + 1],
            ]));
            let fw_size = u32::from_le_bytes([
                data[TI_FW_SIZE_OFFSET],
                data[TI_FW_SIZE_OFFSET + 1],
                data[TI_FW_SIZE_OFFSET + 2],
                data[TI_FW_SIZE_OFFSET + 3],
            ]) as usize;
            let search_start = fw_size.saturating_add(
                TI_HEADER_BLOCK_LEN + TI_DATA_METADATA_LEN * (num_blocks + 1) + TI_METADATA_OFFSET,
            );

            let appconfig_pos = data
                .get(search_start..)
                .and_then(|s| s.windows(4).position(|w| w == TI_APPCONFIG))
                .map(|p| search_start + p);

            let (proj_name, raw_proj) = if let Some(off) = appconfig_pos {
                let slice = data
                    .get(off + TI_PROJ_NAME_OFFSET..off + TI_PROJ_NAME_OFFSET + TI_PROJ_NAME_LEN)
                    .ok_or_else(|| "TI PDC binary is too short to read project name".to_string())?;
                let mut raw = [0u8; TI_PROJ_NAME_LEN];
                raw.copy_from_slice(slice);
                (Some(format_ti_proj_name(&raw)), Some(raw))
            } else {
                (None, None)
            };

            return Ok(PdcImageInfo::Ti {
                ver: Some((major, minor, patch)),
                proj_name,
                raw_proj,
            });
        } else if hdr == TI_APPCONFIG {
            let slice = data
                .get(TI_PROJ_NAME_OFFSET..TI_PROJ_NAME_OFFSET + TI_PROJ_NAME_LEN)
                .ok_or_else(|| "TI appconfig is too short to read project name".to_string())?;
            let mut raw = [0u8; TI_PROJ_NAME_LEN];
            raw.copy_from_slice(slice);
            return Ok(PdcImageInfo::Ti {
                ver: None,
                proj_name: Some(format_ti_proj_name(&raw)),
                raw_proj: Some(raw),
            });
        }
    }

    if data.len() == RTK_TOTAL_SIZE {
        let major = data[RTK_FW_VER_MAJOR];
        let minor = data[RTK_FW_VER_MINOR];
        let cfg = &data[RTK_CONFIG_START..RTK_CONFIG_END];
        let config = cfg[RTK_CFG_VER_OFFSET];
        let proj_name = rtk_proj_name(cfg);
        let file_crc = u32::from_le_bytes([
            data[RTK_CRC_END],
            data[RTK_CRC_END + 1],
            data[RTK_CRC_END + 2],
            data[RTK_CRC_END + 3],
        ]);
        let calc_crc = rtk_crc32(&data[..RTK_CRC_END]);
        if file_crc != calc_crc {
            return Err(format!(
                "CRC32 invalid. Expected 0x{file_crc:08x}, but calculated 0x{calc_crc:08x}"
            ));
        }
        return Ok(PdcImageInfo::RtkFw {
            ver: (major, minor, config),
            proj_name,
        });
    }

    if data.len() == RTK_CONFIG_LEN {
        let cfg_ver = data[RTK_CFG_VER_OFFSET];
        let proj_name = rtk_proj_name(data);
        return Ok(PdcImageInfo::RtkCfg { cfg_ver, proj_name });
    }

    Err("Could not autodetect PDC image type".into())
}

pub fn get_hash_bytes(data: &[u8], path: &Path) -> Result<Vec<u8>, String> {
    match parse_pdc_image(data)? {
        PdcImageInfo::RtkFw { ver, proj_name } => {
            eprintln!(
                "Realtek PDC '{}' version: {}.{}.{} ({})",
                path.display(),
                ver.0,
                ver.1,
                ver.2,
                proj_name.as_deref().unwrap_or("N/A")
            );
            let mut out = vec![ver.0, ver.1, ver.2];
            if let Some(proj) = proj_name.as_deref().filter(|s| !s.is_empty()) {
                out.extend_from_slice(proj.as_bytes());
            }
            Ok(out)
        }
        PdcImageInfo::Ti {
            ver: Some(ver),
            proj_name: Some(proj),
            raw_proj: Some(raw),
        } => {
            eprintln!(
                "TI PDC '{}' version: {}.{}.{} ({})",
                path.display(),
                ver.0,
                ver.1,
                ver.2,
                proj
            );
            let mut out = Vec::with_capacity(3 + TI_PROJ_NAME_LEN);
            out.extend_from_slice(&[ver.0, ver.1, ver.2]);
            out.extend_from_slice(&raw);
            Ok(out)
        }
        PdcImageInfo::Ti { .. } => Err(format!(
            "TI PDC binary '{}' is missing firmware version or appconfig project name",
            path.display()
        )),
        PdcImageInfo::RtkCfg { .. } => Err(format!(
            "Cannot generate PDC hash from config fragment '{}'",
            path.display()
        )),
    }
}

fn cmd_hash(in_path: &Path, output: Option<&Path>) -> Result<(), String> {
    let data =
        fs::read(in_path).map_err(|e| format!("Failed to read {}: {e}", in_path.display()))?;
    let hash = get_hash_bytes(&data, in_path)?;

    if let Some(out_path) = output {
        fs::write(out_path, &hash)
            .map_err(|e| format!("Failed to write {}: {e}", out_path.display()))?;
    } else {
        io::stdout()
            .write_all(&hash)
            .map_err(|e| format!("Failed to write to stdout: {e}"))?;
    }
    Ok(())
}

fn cmd_version(path: &Path) -> Result<(), String> {
    let data = fs::read(path)
        .map_err(|e| format!("Error: File {} does not exist ({e})", path.display()))?;

    match parse_pdc_image(&data)? {
        PdcImageInfo::Ti { ver, proj_name, .. } => {
            let ver_str = ver
                .map(|(ma, mi, pa)| format!("{ma}.{mi}.{pa}"))
                .unwrap_or_else(|| "N/A".into());
            println!("Image Type   : TI");
            println!("Version      : {ver_str}");
            println!("Project Name : {}", proj_name.as_deref().unwrap_or("N/A"));
            Ok(())
        }
        PdcImageInfo::RtkFw { ver, proj_name } => {
            println!("Image Type   : Realtek (Full FW)");
            println!("Version      : {}.{}.{}", ver.0, ver.1, ver.2);
            println!("Project Name : {}", proj_name.as_deref().unwrap_or("None"));
            Ok(())
        }
        PdcImageInfo::RtkCfg { cfg_ver, proj_name } => {
            println!("Image Type   : Realtek (Config Fragment)");
            println!("Version      : x.x.{cfg_ver}");
            println!("Project Name : {}", proj_name.as_deref().unwrap_or("None"));
            Ok(())
        }
    }
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let res = match &cli.command {
        Command::Hash { image, output } => cmd_hash(image, output.as_deref()),
        Command::Version { image } => cmd_version(image),
    };

    if let Err(e) = res {
        eprintln!("Error: {e}");
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn test_file(name: &str) -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../scripts/tests/test_files")
            .join(name)
    }

    #[test]
    fn test_rtk_hash_and_version() {
        let p = test_file("rts5453_v0.44.3.bin");
        let data = fs::read(&p).unwrap();
        let mut expected = vec![0, 44, 3];
        expected.extend_from_slice(b"GOOG0000");
        assert_eq!(get_hash_bytes(&data, &p).unwrap(), expected);

        let p2 = test_file("rts5453_v0.45.4.bin");
        let data2 = fs::read(&p2).unwrap();
        let mut expected2 = vec![0, 45, 4];
        expected2.extend_from_slice(b"GOOG0000");
        assert_eq!(get_hash_bytes(&data2, &p2).unwrap(), expected2);
    }

    #[test]
    fn test_rtk_crc32_validation() {
        let good = fs::read(test_file(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin",
        ))
        .unwrap();
        assert_eq!(
            parse_pdc_image(&good).unwrap(),
            PdcImageInfo::RtkFw {
                ver: (0, 44, 3),
                proj_name: Some("GOOG0H00".into()),
            }
        );

        let bad_path = test_file("ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3__bad_crc.bin");
        let bad = fs::read(&bad_path).unwrap();
        assert!(parse_pdc_image(&bad).unwrap_err().contains("CRC32 invalid"));
        assert!(get_hash_bytes(&bad, &bad_path)
            .unwrap_err()
            .contains("CRC32 invalid"));
    }

    #[test]
    fn test_rtk_cfg_fragment() {
        let cfg = fs::read(test_file("ocelotrvp-GOOG0H00-config.bin")).unwrap();
        assert_eq!(
            parse_pdc_image(&cfg).unwrap(),
            PdcImageInfo::RtkCfg {
                cfg_ver: 3,
                proj_name: Some("GOOG0H00".into()),
            }
        );
    }

    #[test]
    fn test_ti_images() {
        let p_a = test_file("tps6699x-GOOG0J30_00132002_TFU.bin");
        let data_a = fs::read(&p_a).unwrap();
        let mut expected_a = vec![19, 32, 2];
        expected_a.extend_from_slice(b"GOOG0J30");
        assert_eq!(get_hash_bytes(&data_a, &p_a).unwrap(), expected_a);

        let p_a2 = test_file("tps6699x-GOOG0J30_00132008_TFU.bin");
        let data_a2 = fs::read(&p_a2).unwrap();
        let mut expected_a2 = vec![19, 32, 8];
        expected_a2.extend_from_slice(b"GOOG0J30");
        assert_eq!(get_hash_bytes(&data_a2, &p_a2).unwrap(), expected_a2);

        let p_b = test_file("tps6699xb-GOOG0b00_00160001_TFU.bin");
        let data_b = fs::read(&p_b).unwrap();
        let mut expected_b = vec![22, 0, 1];
        expected_b.extend_from_slice(b"GOOG0b00");
        assert_eq!(get_hash_bytes(&data_b, &p_b).unwrap(), expected_b);
    }
}

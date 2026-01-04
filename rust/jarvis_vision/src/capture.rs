use std::env;
use std::fs;
use std::process::Command;

use tempfile::Builder;

pub fn take_screenshot_png() -> Option<Vec<u8>> {
    let tmp = Builder::new().suffix(".png").tempfile().ok()?;
    let path = tmp.path();
    let path_str = path.to_string_lossy().to_string();

    let session = env::var("XDG_SESSION_TYPE").unwrap_or_default();
    let is_x11 = session.eq_ignore_ascii_case("x11")
        || (env::var("DISPLAY").is_ok() && env::var("WAYLAND_DISPLAY").is_err());

    // Prefer the fastest capture tool for the active session.
    let commands: [(&str, Vec<String>); 3] = if is_x11 {
        [
            ("scrot", vec![path_str.clone()]),
            ("gnome-screenshot", vec!["-f".to_string(), path_str.clone()]),
            ("grim", vec![path_str.clone()]),
        ]
    } else {
        [
            ("gnome-screenshot", vec!["-f".to_string(), path_str.clone()]),
            ("grim", vec![path_str.clone()]),
            ("scrot", vec![path_str.clone()]),
        ]
    };

    for (cmd, args) in commands.iter() {
        if run_command(cmd, args) {
            if let Ok(bytes) = fs::read(path) {
                if bytes.len() >= 12 {
                    return Some(bytes);
                }
            }
        }
    }

    None
}

fn run_command(cmd: &str, args: &[String]) -> bool {
    Command::new(cmd)
        .args(args)
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

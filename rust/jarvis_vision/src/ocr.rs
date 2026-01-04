use std::env;
use std::io::{Cursor, Write};
use std::process::Command;

use image::imageops::FilterType;
use image::{DynamicImage, GenericImageView, ImageFormat};
use tempfile::NamedTempFile;

const OCR_LANG: &str = "por+eng";
const DEFAULT_MAX_DIM: u32 = 720;
const DEFAULT_FAST_MAX_DIM: u32 = 540;
const DEFAULT_PSM: i32 = 3;
const DEFAULT_FAST_PSM: i32 = 11;
const DEFAULT_OEM: i32 = 1;

pub fn ocr_text(png_bytes: &[u8]) -> String {
    if png_bytes.len() < 12 {
        return String::new();
    }
    let fast_dim = ocr_fast_max_dim();
    let full_dim = ocr_max_dim();
    let fast_psm = ocr_fast_psm();
    let full_psm = ocr_psm();
    let use_fast = fast_dim > 0 && (fast_dim != full_dim || fast_psm != full_psm);

    if use_fast {
        let fast_text = ocr_text_with_params(png_bytes, fast_dim, fast_psm);
        if !fast_text.is_empty() {
            return fast_text;
        }
    }

    ocr_text_with_params(png_bytes, full_dim, full_psm)
}

pub fn ocr_tsv(png_bytes: &[u8]) -> Option<String> {
    if png_bytes.len() < 12 {
        return None;
    }
    if prefer_leptess() {
        if let Some(text) = ocr_tsv_leptess(png_bytes) {
            return Some(text);
        }
    }
    run_tesseract(png_bytes, ocr_psm(), &["tsv"]).ok()
}

fn ocr_text_with_params(png_bytes: &[u8], max_dim: u32, psm: i32) -> String {
    let bytes = downscale_with_max_dim(png_bytes, max_dim);
    if prefer_leptess() {
        if let Some(text) = ocr_text_leptess(&bytes, psm) {
            return text;
        }
    }
    run_tesseract(&bytes, psm, &[]).unwrap_or_default()
}

fn run_tesseract(png_bytes: &[u8], psm: i32, extra_args: &[&str]) -> Result<String, ()> {
    let mut tmp = NamedTempFile::new().map_err(|_| ())?;
    tmp.write_all(png_bytes).map_err(|_| ())?;
    let path = tmp.path().to_string_lossy().to_string();

    let mut cmd = Command::new("tesseract");
    cmd.arg(&path)
        .arg("stdout")
        .arg("-l")
        .arg(OCR_LANG)
        .arg("--oem")
        .arg(ocr_oem().to_string())
        .arg("--psm")
        .arg(psm.to_string());
    for arg in extra_args {
        cmd.arg(arg);
    }

    let output = cmd.output().map_err(|_| ())?;
    if !output.status.success() {
        return Err(());
    }

    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

fn ocr_max_dim() -> u32 {
    env::var("JARVIS_OCR_MAX_DIM")
        .ok()
        .and_then(|value| value.parse::<u32>().ok())
        .unwrap_or(DEFAULT_MAX_DIM)
}

fn ocr_fast_max_dim() -> u32 {
    env::var("JARVIS_OCR_FAST_MAX_DIM")
        .ok()
        .and_then(|value| value.parse::<u32>().ok())
        .unwrap_or(DEFAULT_FAST_MAX_DIM)
}

fn ocr_psm() -> i32 {
    env::var("JARVIS_OCR_PSM")
        .ok()
        .and_then(|value| value.parse::<i32>().ok())
        .unwrap_or(DEFAULT_PSM)
}

fn ocr_fast_psm() -> i32 {
    env::var("JARVIS_OCR_FAST_PSM")
        .ok()
        .and_then(|value| value.parse::<i32>().ok())
        .unwrap_or(DEFAULT_FAST_PSM)
}

fn ocr_oem() -> i32 {
    env::var("JARVIS_OCR_OEM")
        .ok()
        .and_then(|value| value.parse::<i32>().ok())
        .unwrap_or(DEFAULT_OEM)
}

fn debug_enabled() -> bool {
    env::var("JARVIS_OCR_DEBUG")
        .map(|value| matches!(value.as_str(), "1" | "true" | "yes" | "on"))
        .unwrap_or(false)
}

fn downscale_with_max_dim(png_bytes: &[u8], max_dim: u32) -> Vec<u8> {
    if max_dim == 0 {
        return png_bytes.to_vec();
    }

    let img = match image::load_from_memory(png_bytes) {
        Ok(img) => img,
        Err(err) => {
            if debug_enabled() {
                eprintln!("ocr: decode failed: {err}");
            }
            return png_bytes.to_vec();
        }
    };

    let (width, height) = img.dimensions();
    let max_side = width.max(height);
    if max_side <= max_dim {
        if debug_enabled() {
            eprintln!("ocr: no downscale ({}x{})", width, height);
        }
        return png_bytes.to_vec();
    }

    let scale = max_dim as f32 / max_side as f32;
    let new_width = ((width as f32) * scale).round().max(1.0) as u32;
    let new_height = ((height as f32) * scale).round().max(1.0) as u32;
    let resized = img.resize(new_width, new_height, FilterType::Triangle).to_luma8();
    let resized_img = DynamicImage::ImageLuma8(resized);

    let mut output = Vec::new();
    let mut cursor = Cursor::new(&mut output);
    if resized_img.write_to(&mut cursor, ImageFormat::Png).is_err() {
        if debug_enabled() {
            eprintln!("ocr: resize encode failed");
        }
        return png_bytes.to_vec();
    }

    if debug_enabled() {
        eprintln!(
            "ocr: downscale {}x{} -> {}x{} ({} bytes, max_dim={})",
            width,
            height,
            new_width,
            new_height,
            output.len(),
            max_dim
        );
    }

    output
}

fn prefer_leptess() -> bool {
    if !cfg!(feature = "leptess") {
        return false;
    }
    match env::var("JARVIS_OCR_BACKEND") {
        Ok(value) => matches!(
            value.trim().to_lowercase().as_str(),
            "leptess" | "lib" | "native"
        ),
        Err(_) => false,
    }
}

#[cfg(feature = "leptess")]
use std::cell::RefCell;
#[cfg(feature = "leptess")]
use leptess::{LepTess, Variable};

#[cfg(feature = "leptess")]
enum LeptessState {
    Uninitialized,
    Failed,
    Ready(LepTess),
}

#[cfg(feature = "leptess")]
thread_local! {
    static LEPTESS_STATE: RefCell<LeptessState> = RefCell::new(LeptessState::Uninitialized);
}

#[cfg(feature = "leptess")]
fn with_leptess<F, R>(f: F) -> Option<R>
where
    F: FnOnce(&mut LepTess) -> Option<R>,
{
    LEPTESS_STATE.with(|state| {
        let mut state = state.borrow_mut();
        match &mut *state {
            LeptessState::Ready(tess) => return f(tess),
            LeptessState::Failed => return None,
            LeptessState::Uninitialized => {
                match LepTess::new(None, OCR_LANG) {
                    Ok(mut tess) => {
                        let _ = tess.set_variable(Variable::TesseditPagesegMode, "3");
                        let _ = tess.set_variable(Variable::TesseditOcrEngineMode, "1");
                        *state = LeptessState::Ready(tess);
                    }
                    Err(_) => {
                        *state = LeptessState::Failed;
                        return None;
                    }
                }
            }
        }
        match &mut *state {
            LeptessState::Ready(tess) => f(tess),
            _ => None,
        }
    })
}

#[cfg(feature = "leptess")]
fn ocr_text_leptess(png_bytes: &[u8], psm: i32) -> Option<String> {
    with_leptess(|tess| {
        if png_bytes.len() < 12 {
            return None;
        }
        if tess.set_image_from_mem(png_bytes).is_err() {
            return None;
        }
        let _ = tess.set_variable(Variable::TesseditPagesegMode, &psm.to_string());
        tess.set_fallback_source_resolution(96);
        tess.get_utf8_text().ok().map(|text| text.trim().to_string())
    })
}

#[cfg(feature = "leptess")]
fn ocr_tsv_leptess(png_bytes: &[u8]) -> Option<String> {
    with_leptess(|tess| {
        if png_bytes.len() < 12 {
            return None;
        }
        if tess.set_image_from_mem(png_bytes).is_err() {
            return None;
        }
        tess.set_fallback_source_resolution(96);
        tess.get_tsv_text(0).ok().map(|text| text.trim().to_string())
    })
}

#[cfg(not(feature = "leptess"))]
fn ocr_text_leptess(_png_bytes: &[u8], _psm: i32) -> Option<String> {
    None
}

#[cfg(not(feature = "leptess"))]
fn ocr_tsv_leptess(_png_bytes: &[u8]) -> Option<String> {
    None
}

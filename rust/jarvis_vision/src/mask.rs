use std::io::Cursor;

use image::imageops;
use image::{DynamicImage, GenericImageView, ImageBuffer, ImageFormat, Rgba};
use once_cell::sync::Lazy;
use regex::Regex;

use crate::ocr;

static SENSITIVE_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        Regex::new(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b").unwrap(),
        Regex::new(r"\b\d{11}\b").unwrap(),
        Regex::new(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b").unwrap(),
        Regex::new(r"\b\d{14}\b").unwrap(),
        Regex::new(r"\b(?:\d{4}[-\s]?){3,4}\d{1,4}\b").unwrap(),
        Regex::new(r"\b(?:cvv|cvc|csc)[\s:]*\d{3,4}\b").unwrap(),
        Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b").unwrap(),
        Regex::new(r"\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}\b").unwrap(),
        Regex::new(r"(?:senha|password|pwd)[\s:]*\S+").unwrap(),
        Regex::new(r"\b(?:pix|chave)[\s:]*\S+").unwrap(),
        Regex::new(r"\b(?:conta|agencia)[\s:]*\d+[-\s]?\d*\b").unwrap(),
        Regex::new(r"r\$\s*[\d.,]+").unwrap(),
        Regex::new(r"\b\d{1,2}\.\d{3}\.\d{3}-?[0-9Xx]\b").unwrap(),
    ]
});

#[derive(Debug, Clone, Copy)]
struct Region {
    x: i32,
    y: i32,
    w: i32,
    h: i32,
}

pub fn mask_sensitive_png(png_bytes: &[u8], use_blur: bool) -> Option<Vec<u8>> {
    let mut img = image::load_from_memory(png_bytes).ok()?;
    let tsv = ocr::ocr_tsv(png_bytes)?;
    let regions = find_sensitive_regions(&tsv, 10)?;

    if regions.is_empty() {
        return Some(png_bytes.to_vec());
    }

    for region in regions {
        apply_mask(&mut img, region, use_blur, 15.0);
    }

    let mut output = Vec::new();
    let mut cursor = Cursor::new(&mut output);
    if img.write_to(&mut cursor, ImageFormat::Png).is_err() {
        return None;
    }
    Some(output)
}

fn find_sensitive_regions(tsv: &str, expand_px: i32) -> Option<Vec<Region>> {
    let mut regions = Vec::new();

    for (idx, line) in tsv.lines().enumerate() {
        if idx == 0 {
            continue;
        }
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() < 12 {
            continue;
        }
        let text = parts[11].trim();
        if text.is_empty() {
            continue;
        }
        if !matches_sensitive(text) {
            continue;
        }

        let left = parts[6].parse::<i32>().unwrap_or(0);
        let top = parts[7].parse::<i32>().unwrap_or(0);
        let width = parts[8].parse::<i32>().unwrap_or(0);
        let height = parts[9].parse::<i32>().unwrap_or(0);

        regions.push(Region {
            x: left - expand_px,
            y: top - expand_px,
            w: width + 2 * expand_px,
            h: height + 2 * expand_px,
        });
    }

    Some(regions)
}

fn matches_sensitive(text: &str) -> bool {
    let text = text.to_lowercase();
    for pattern in SENSITIVE_PATTERNS.iter() {
        if pattern.is_match(&text) {
            return true;
        }
    }
    false
}

fn apply_mask(img: &mut DynamicImage, region: Region, use_blur: bool, blur_radius: f32) {
    let (width, height) = img.dimensions();
    let x1 = region.x.max(0) as u32;
    let y1 = region.y.max(0) as u32;
    let x2 = (region.x + region.w).max(0) as u32;
    let y2 = (region.y + region.h).max(0) as u32;

    if x1 >= width || y1 >= height {
        return;
    }

    let x2 = x2.min(width);
    let y2 = y2.min(height);
    if x2 <= x1 || y2 <= y1 {
        return;
    }

    let w = x2 - x1;
    let h = y2 - y1;

    if use_blur {
        let cropped = img.crop_imm(x1, y1, w, h).blur(blur_radius);
        imageops::overlay(img, &cropped, x1 as i64, y1 as i64);
    } else {
        let fill = ImageBuffer::from_pixel(w, h, Rgba([0, 0, 0, 255]));
        let overlay = DynamicImage::ImageRgba8(fill);
        imageops::overlay(img, &overlay, x1 as i64, y1 as i64);
    }
}

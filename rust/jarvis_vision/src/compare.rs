use image::imageops::FilterType;

pub fn compare_png(png_a: &[u8], png_b: &[u8]) -> Result<f32, String> {
    let img_a = image::load_from_memory(png_a).map_err(|err| err.to_string())?;
    let img_b = image::load_from_memory(png_b).map_err(|err| err.to_string())?;

    let img_a = img_a.resize(256, 256, FilterType::Triangle).to_luma8();
    let img_b = img_b.resize(256, 256, FilterType::Triangle).to_luma8();

    if img_a.dimensions() != img_b.dimensions() {
        return Ok(0.0);
    }

    let mut total_diff: u64 = 0;
    for (p1, p2) in img_a.pixels().zip(img_b.pixels()) {
        total_diff += (p1[0] as i16 - p2[0] as i16).abs() as u64;
    }

    let pixel_count = (img_a.width() as u64) * (img_a.height() as u64);
    let max_diff = 255u64 * pixel_count;

    if max_diff == 0 {
        return Ok(0.0);
    }

    let similarity = 1.0 - (total_diff as f32 / max_diff as f32);
    Ok(similarity.clamp(0.0, 1.0))
}

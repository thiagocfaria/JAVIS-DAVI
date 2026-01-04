use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyModule};
use pyo3::Bound;

mod capture;
mod compare;
mod detect;
mod mask;
mod ocr;
mod policy;
mod validator;

#[pyfunction]
fn take_screenshot_png(py: Python<'_>) -> PyResult<Option<Py<PyBytes>>> {
    Ok(capture::take_screenshot_png().map(|bytes| PyBytes::new_bound(py, &bytes).into()))
}

#[pyfunction]
fn ocr_text(png_bytes: &[u8]) -> PyResult<String> {
    Ok(ocr::ocr_text(png_bytes))
}

#[pyfunction]
fn detect_captcha(text: &str) -> PyResult<bool> {
    Ok(detect::detect_captcha(text))
}

#[pyfunction]
fn detect_error(text: &str) -> PyResult<Option<String>> {
    Ok(detect::detect_error(text))
}

#[pyfunction]
fn compare_png(png_a: &[u8], png_b: &[u8]) -> PyResult<f32> {
    Ok(compare::compare_png(png_a, png_b).unwrap_or(0.0))
}

#[pymodule]
fn jarvis_vision(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(take_screenshot_png, m)?)?;
    m.add_function(wrap_pyfunction!(ocr_text, m)?)?;
    m.add_function(wrap_pyfunction!(detect_captcha, m)?)?;
    m.add_function(wrap_pyfunction!(detect_error, m)?)?;
    m.add_function(wrap_pyfunction!(compare_png, m)?)?;
    m.add_class::<validator::Validator>()?;
    Ok(())
}

use std::collections::{hash_map::DefaultHasher, HashMap};
use std::fs;
use std::hash::{Hash, Hasher};
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use pyo3::Bound;

use crate::{capture, detect, mask, ocr, policy};

#[derive(Clone)]
struct ValidationCheckpoint {
    #[allow(dead_code)]
    ocr_text: String,
    #[allow(dead_code)]
    timestamp: f64,
    expected_elements: Vec<String>,
}

#[pyclass]
pub struct Validator {
    screenshot_dir: PathBuf,
    enable_ocr: bool,
    save_screenshots: bool,
    checkpoints: HashMap<String, ValidationCheckpoint>,
    last_ocr_hash: Option<u64>,
    last_ocr_text: String,
}

#[pymethods]
impl Validator {
    #[new]
    #[pyo3(signature = (screenshot_dir=None, enable_ocr=true, save_screenshots=false))]
    fn new(screenshot_dir: Option<String>, enable_ocr: bool, save_screenshots: bool) -> Self {
        let dir = screenshot_dir
            .map(PathBuf::from)
            .unwrap_or_else(|| std::env::temp_dir().join("jarvis_screenshots"));
        if save_screenshots {
            let _ = fs::create_dir_all(&dir);
        }

        Self {
            screenshot_dir: dir,
            enable_ocr,
            save_screenshots,
            checkpoints: HashMap::new(),
            last_ocr_hash: None,
            last_ocr_text: String::new(),
        }
    }

    fn take_screenshot_png(&mut self, py: Python<'_>) -> Option<Py<PyBytes>> {
        capture::take_screenshot_png().map(|bytes| PyBytes::new_bound(py, &bytes).into())
    }

    fn ocr_text(&mut self, png_bytes: &[u8]) -> String {
        if !self.enable_ocr {
            return String::new();
        }
        self.ocr_text_cached(png_bytes)
    }

    fn save_checkpoint(&mut self, name: String, expected_elements: Option<Vec<String>>) -> bool {
        let screenshot = match capture::take_screenshot_png() {
            Some(bytes) => bytes,
            None => return false,
        };

        let ocr_text = if self.enable_ocr {
            self.ocr_text_cached(&screenshot)
        } else {
            String::new()
        };

        self.checkpoints.insert(
            name.clone(),
            ValidationCheckpoint {
                ocr_text,
                timestamp: now_ts(),
                expected_elements: expected_elements.unwrap_or_default(),
            },
        );

        if self.save_screenshots {
            let file_name = format!("checkpoint_{}_{}.png", name, now_ts() as i64);
            let path = self.screenshot_dir.join(file_name);
            let _ = fs::write(path, screenshot);
        }

        true
    }

    fn compare_with_checkpoint(&mut self, py: Python<'_>, name: String, similarity_threshold: Option<f32>) -> PyResult<PyObject> {
        let checkpoint = match self.checkpoints.get(&name) {
            Some(checkpoint) => checkpoint.clone(),
            None => {
                return Ok(result_dict(
                    py,
                    "unknown",
                    1.0,
                    Some("Checkpoint not found"),
                    None,
                    None,
                ));
            }
        };

        let _ = similarity_threshold;

        let screenshot = match capture::take_screenshot_png() {
            Some(bytes) => bytes,
            None => {
                return Ok(result_dict(
                    py,
                    "unknown",
                    1.0,
                    Some("Could not take screenshot"),
                    None,
                    None,
                ));
            }
        };

        let current_text = if self.enable_ocr {
            self.ocr_text_cached(&screenshot)
        } else {
            String::new()
        };
        let current_lower = current_text.to_lowercase();

        let mut missing = Vec::new();
        for expected in checkpoint.expected_elements.iter() {
            if !current_lower.contains(&expected.to_lowercase()) {
                missing.push(expected.clone());
            }
        }

        if !missing.is_empty() {
            let confidence = if checkpoint.expected_elements.is_empty() {
                0.0
            } else {
                1.0 - (missing.len() as f32 / checkpoint.expected_elements.len() as f32)
            };
            let details = Some(details_missing(py, &missing, &checkpoint.expected_elements));
            return Ok(result_dict(
                py,
                "failed",
                confidence,
                None,
                details,
                Some(&current_text),
            ));
        }

        let details = Some(details_matched(py, &checkpoint.expected_elements));
        Ok(result_dict(py, "ok", 1.0, None, details, Some(&current_text)))
    }

    fn detect_captcha_or_2fa(&mut self, png_bytes: Option<&[u8]>) -> bool {
        if !self.enable_ocr {
            return false;
        }

        let screenshot = match png_bytes {
            Some(bytes) => bytes.to_vec(),
            None => match capture::take_screenshot_png() {
                Some(bytes) => bytes,
                None => return false,
            },
        };

        let text = self.ocr_text_cached(&screenshot);
        detect::detect_captcha(&text)
    }

    fn detect_error_modal(&mut self, png_bytes: Option<&[u8]>) -> Option<String> {
        if !self.enable_ocr {
            return None;
        }

        let screenshot = match png_bytes {
            Some(bytes) => bytes.to_vec(),
            None => match capture::take_screenshot_png() {
                Some(bytes) => bytes,
                None => return None,
            },
        };

        let text = self.ocr_text_cached(&screenshot);
        detect::detect_error(&text)
    }

    fn validate_action(&mut self, py: Python<'_>, action_type: String, params: Option<&Bound<'_, PyDict>>) -> PyResult<PyObject> {
        let (status, confidence, error) = self.validate_action_internal(&action_type, params);
        Ok(result_dict(py, &status, confidence, error.as_deref(), None, None))
    }

    fn get_masked_screenshot_for_ai(
        &mut self,
        py: Python<'_>,
        app_name: Option<String>,
        url: Option<String>,
    ) -> Option<Py<PyBytes>> {
        let app_name = app_name.unwrap_or_default();
        let url = url.unwrap_or_default();

        if !policy::is_screenshot_allowed(&app_name, &url) {
            return None;
        }

        let screenshot = capture::take_screenshot_png()?;
        mask::mask_sensitive_png(&screenshot, true)
            .map(|bytes| PyBytes::new_bound(py, &bytes).into())
    }
}

impl Validator {
    fn ocr_text_cached(&mut self, png_bytes: &[u8]) -> String {
        if ocr_cache_disabled() {
            return ocr::ocr_text(png_bytes);
        }
        let hash = hash_bytes(png_bytes);
        if self.last_ocr_hash == Some(hash) {
            return self.last_ocr_text.clone();
        }
        let text = ocr::ocr_text(png_bytes);
        self.last_ocr_hash = Some(hash);
        self.last_ocr_text = text.clone();
        text
    }

    fn validate_action_internal(
        &mut self,
        action_type: &str,
        params: Option<&Bound<'_, PyDict>>,
    ) -> (String, f32, Option<String>) {
        let screenshot = capture::take_screenshot_png();
        let (text, text_lower) = if self.enable_ocr {
            if let Some(ref bytes) = screenshot {
                let txt = self.ocr_text_cached(bytes);
                let lower = txt.to_lowercase();
                (txt, lower)
            } else {
                (String::new(), String::new())
            }
        } else {
            (String::new(), String::new())
        };

        if !text.is_empty() {
            if detect::detect_captcha(&text) {
                return ("requires_human".to_string(), 1.0, None);
            }
            if let Some(err) = detect::detect_error(&text) {
                return ("failed".to_string(), 1.0, Some(err));
            }
        }

        match action_type {
            "open_app" => {
                if screenshot.is_none() || !self.enable_ocr {
                    return ("ok".to_string(), 0.5, None);
                }
                let app = get_param_string(params, "app");
                if !app.is_empty() && text_lower.contains(&app.to_lowercase()) {
                    return ("ok".to_string(), 0.9, None);
                }
                ("ok".to_string(), 0.6, None)
            }
            "open_url" => {
                if screenshot.is_none() || !self.enable_ocr {
                    return ("ok".to_string(), 0.5, None);
                }
                let url = get_param_string(params, "url");
                let domain = url
                    .replace("https://", "")
                    .replace("http://", "")
                    .split('/')
                    .next()
                    .unwrap_or("")
                    .to_lowercase();
                if !domain.is_empty() && text_lower.contains(&domain) {
                    return ("ok".to_string(), 0.9, None);
                }
                ("ok".to_string(), 0.6, None)
            }
            "type_text" => {
                if screenshot.is_none() || !self.enable_ocr {
                    return ("ok".to_string(), 0.5, None);
                }
                let expected = get_param_string(params, "text");
                if expected.is_empty() {
                    return ("ok".to_string(), 0.5, None);
                }
                if text_lower.contains(&expected.to_lowercase()) {
                    return ("ok".to_string(), 0.95, None);
                }
                let expected_lower = expected.to_lowercase();
                let words: Vec<&str> = expected_lower.split_whitespace().collect();
                let found = words.iter().filter(|w| text_lower.contains(**w)).count();
                let ratio = if words.is_empty() { 0.0 } else { found as f32 / words.len() as f32 };
                if ratio >= 0.5 {
                    return ("ok".to_string(), 0.7, None);
                }
                ("ok".to_string(), 0.5, None)
            }
            _ => ("ok".to_string(), 0.8, None),
        }
    }
}

fn get_param_string(params: Option<&Bound<'_, PyDict>>, key: &str) -> String {
    let params = match params {
        Some(params) => params,
        None => return String::new(),
    };
    let value = match params.get_item(key) {
        Ok(Some(value)) => value,
        _ => return String::new(),
    };
    value.extract::<String>().unwrap_or_default()
}

fn result_dict(
    py: Python<'_>,
    status: &str,
    confidence: f32,
    error: Option<&str>,
    details: Option<PyObject>,
    ocr_text: Option<&str>,
) -> PyObject {
    let dict = PyDict::new_bound(py);
    let _ = dict.set_item("status", status);
    let _ = dict.set_item("confidence", confidence);
    let _ = dict.set_item("error", error.unwrap_or(""));
    if let Some(details) = details {
        let _ = dict.set_item("details", details);
    }
    if let Some(text) = ocr_text {
        let _ = dict.set_item("ocr_text", text);
    }
    dict.into_py(py)
}

fn details_missing(py: Python<'_>, missing: &[String], expected: &[String]) -> PyObject {
    let dict = PyDict::new_bound(py);
    let _ = dict.set_item("missing_elements", missing);
    let _ = dict.set_item("expected", expected);
    dict.into_py(py)
}

fn details_matched(py: Python<'_>, expected: &[String]) -> PyObject {
    let dict = PyDict::new_bound(py);
    let _ = dict.set_item("matched_elements", expected);
    dict.into_py(py)
}

fn now_ts() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

fn ocr_cache_disabled() -> bool {
    std::env::var("JARVIS_OCR_DISABLE_CACHE")
        .map(|value| matches!(value.as_str(), "1" | "true" | "yes" | "on"))
        .unwrap_or(false)
}

fn hash_bytes(bytes: &[u8]) -> u64 {
    let mut hasher = DefaultHasher::new();
    bytes.hash(&mut hasher);
    hasher.finish()
}

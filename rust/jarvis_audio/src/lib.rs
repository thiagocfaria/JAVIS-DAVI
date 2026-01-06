use pyo3::prelude::*;
use pyo3::types::PyDict;

const ENERGY_THRESHOLD: f64 = 500.0; // limiar simples; ajustável se necessário

fn frame_energy(frame: &[i16]) -> f64 {
    if frame.is_empty() {
        return 0.0;
    }
    let sum: i64 = frame.iter().map(|s| (*s as i64).abs()).sum();
    sum as f64 / frame.len() as f64
}

fn trim_audio(
    samples: &[i16],
    sample_rate: i32,
    frame_ms: i32,
    pre_roll_ms: i32,
    post_roll_ms: i32,
    silence_ms: i32,
) -> (Vec<i16>, bool, usize, usize, usize, usize) {
    if sample_rate <= 0 || frame_ms <= 0 {
        return (Vec::new(), false, 0, 0, 0, 0);
    }

    let frame_samples = (sample_rate as usize * frame_ms as usize) / 1000;
    if frame_samples == 0 {
        return (Vec::new(), false, 0, 0, 0, 0);
    }

    let total_frames = samples.len() / frame_samples;
    if total_frames == 0 {
        return (Vec::new(), false, 0, 0, 0, 0);
    }

    let silence_frames = std::cmp::max(1, (silence_ms.max(0) as usize) / (frame_ms as usize));
    let pre_roll_frames = std::cmp::max(0, pre_roll_ms.max(0) as usize / frame_ms as usize);
    let post_roll_frames = std::cmp::max(0, post_roll_ms.max(0) as usize / frame_ms as usize);

    let mut speech_detected = false;
    let mut start_frame: Option<usize> = None;
    let mut last_speech_frame: usize = 0;
    let mut silence_run = 0usize;

    for frame_idx in 0..total_frames {
        let start = frame_idx * frame_samples;
        let end = start + frame_samples;
        let energy = frame_energy(&samples[start..end]);
        let is_speech = energy >= ENERGY_THRESHOLD;

        if !speech_detected && is_speech {
            speech_detected = true;
            let s = frame_idx.saturating_sub(pre_roll_frames);
            start_frame = Some(s);
            last_speech_frame = frame_idx;
            silence_run = 0;
            continue;
        }

        if speech_detected {
            if is_speech {
                last_speech_frame = frame_idx;
                silence_run = 0;
            } else {
                silence_run += 1;
                if silence_run >= silence_frames {
                    break;
                }
            }
        }
    }

    if !speech_detected {
        return (Vec::new(), false, total_frames, 0, 0, 0);
    }

    let start = start_frame.unwrap_or(0);
    let mut end = std::cmp::min(total_frames, last_speech_frame + 1 + post_roll_frames);
    if end <= start {
        end = std::cmp::min(start + 1, total_frames);
    }
    let frames_out = end - start;

    let start_sample = start * frame_samples;
    let end_sample = end * frame_samples;
    let trimmed = samples[start_sample..end_sample].to_vec();

    (trimmed, true, total_frames, frames_out, start, end.saturating_sub(1))
}

fn pcm_bytes_to_samples(pcm: &[u8]) -> Vec<i16> {
    let mut samples = Vec::with_capacity(pcm.len() / 2);
    let mut i = 0;
    while i + 1 < pcm.len() {
        let b0 = pcm[i] as u16;
        let b1 = pcm[i + 1] as u16;
        samples.push(i16::from_le_bytes([b0 as u8, b1 as u8]));
        i += 2;
    }
    samples
}

fn samples_to_bytes(samples: &[i16]) -> Vec<u8> {
    let mut out = Vec::with_capacity(samples.len() * 2);
    for s in samples {
        out.extend_from_slice(&s.to_le_bytes());
    }
    out
}

#[pyfunction]
fn trim_until_silence(
    py: Python<'_>,
    pcm: &PyAny,
    sample_rate: i32,
    frame_ms: i32,
    pre_roll_ms: i32,
    post_roll_ms: i32,
    silence_ms: i32,
) -> PyResult<(PyObject, bool, PyObject)> {
    let pcm_bytes: Vec<u8> = pcm.extract()?;
    let (trimmed, speech_detected, frames_total, frames_out, start_frame, end_frame) =
        py.allow_threads(|| {
            let samples = pcm_bytes_to_samples(&pcm_bytes);
            trim_audio(
                &samples,
                sample_rate,
                frame_ms,
                pre_roll_ms,
                post_roll_ms,
                silence_ms,
            )
        });

    let trimmed_bytes = samples_to_bytes(&trimmed);
    let stats = PyDict::new(py);
    stats.set_item("frames_total", frames_total)?;
    stats.set_item("frames_out", frames_out)?;
    stats.set_item("start_frame", start_frame)?;
    stats.set_item("end_frame", end_frame)?;
    stats.set_item("duration_ms", (frames_out as i32 * frame_ms) as i64)?;

    Ok((trimmed_bytes.into_py(py), speech_detected, stats.into()))
}

#[pyfunction]
fn check_speech_present(py: Python<'_>, pcm: &PyAny, sample_rate: i32, frame_ms: i32) -> PyResult<bool> {
    let pcm_bytes: Vec<u8> = pcm.extract()?;
    let result = py.allow_threads(|| {
        let samples = pcm_bytes_to_samples(&pcm_bytes);
        let frame_samples = (sample_rate as usize * frame_ms as usize) / 1000;
        if frame_samples == 0 || samples.is_empty() {
            return false;
        }
        let total_frames = samples.len() / frame_samples;
        for idx in 0..total_frames {
            let start = idx * frame_samples;
            let end = start + frame_samples;
            let energy = frame_energy(&samples[start..end]);
            if energy >= ENERGY_THRESHOLD {
                return true;
            }
        }
        false
    });
    Ok(result)
}

#[pymodule]
fn jarvis_audio(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(trim_until_silence, m)?)?;
    m.add_function(wrap_pyfunction!(check_speech_present, m)?)?;
    Ok(())
}

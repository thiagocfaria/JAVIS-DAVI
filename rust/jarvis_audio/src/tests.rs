use std::f32::consts::PI;

use crate::trim_until_silence;

fn gen_silence_ms(ms: i32, sample_rate: i32) -> Vec<i16> {
    let total_samples = (sample_rate as f32 * (ms as f32 / 1000.0)) as usize;
    vec![0i16; total_samples]
}

fn gen_tone_ms(ms: i32, sample_rate: i32, freq: f32, amplitude: f32) -> Vec<i16> {
    let total_samples = (sample_rate as f32 * (ms as f32 / 1000.0)) as usize;
    let mut out = Vec::with_capacity(total_samples);
    for n in 0..total_samples {
        let t = n as f32 / sample_rate as f32;
        let sample = (amplitude * (2.0 * PI * freq * t).sin()).clamp(-1.0, 1.0);
        out.push((sample * i16::MAX as f32) as i16);
    }
    out
}

fn as_bytes(samples: &[i16]) -> Vec<u8> {
    let mut out = Vec::with_capacity(samples.len() * 2);
    for s in samples {
        out.extend_from_slice(&s.to_le_bytes());
    }
    out
}

#[test]
fn trim_removes_long_leading_silence_and_detects_speech() {
    let sr = 16_000;
    let frame_ms = 20;
    let pre_roll_ms = 200;
    let post_roll_ms = 200;
    let silence_ms = 300;

    let mut pcm: Vec<i16> = Vec::new();
    pcm.extend(gen_silence_ms(2000, sr));
    pcm.extend(gen_tone_ms(600, sr, 440.0, 0.3));
    pcm.extend(gen_silence_ms(600, sr));

    let pcm_bytes = as_bytes(&pcm);
    let (out, speech, stats) = trim_until_silence(
        pyo3::Python::acquire_gil().python(),
        pyo3::types::PyBytes::new(pyo3::Python::acquire_gil().python(), &pcm_bytes),
        sr,
        frame_ms,
        pre_roll_ms,
        post_roll_ms,
        silence_ms,
    )
    .expect("trim");

    assert!(speech, "fala deve ser detectada");
    let input_ms = (pcm.len() as f32 / sr as f32) * 1000.0;
    let out_ms = (out.len() as f32 / 2.0 / sr as f32) * 1000.0;
    assert!(
        out_ms < input_ms * 0.6,
        "saida deve ser bem menor que entrada ({} ms vs {} ms)",
        out_ms,
        input_ms
    );
    let frames_total: i64 = stats.get_item("frames_total").unwrap().extract().unwrap();
    assert!(frames_total > 0);
}

#[test]
fn trim_returns_false_for_pure_silence() {
    let sr = 16_000;
    let frame_ms = 20;
    let pcm = gen_silence_ms(1500, sr);
    let pcm_bytes = as_bytes(&pcm);

    let (out, speech, _stats) = trim_until_silence(
        pyo3::Python::acquire_gil().python(),
        pyo3::types::PyBytes::new(pyo3::Python::acquire_gil().python(), &pcm_bytes),
        sr,
        frame_ms,
        200,
        200,
        300,
    )
    .expect("trim silence");

    assert!(!speech, "nao deve detectar fala em silencio puro");
    assert!(out.is_empty(), "saida deve ser vazia em silencio puro");
}

// Testes básicos de regressão para jarvis_vision
// Testa funcionalidades principais sem depender de ambiente gráfico

// Importa módulos internos para testes
#[path = "../src/detect.rs"]
mod detect;

#[path = "../src/compare.rs"]
mod compare;

#[path = "../src/ocr.rs"]
mod ocr;

#[test]
fn test_detect_captcha() {
    // Testa detecção de CAPTCHA
    assert!(detect::detect_captcha("Please complete the captcha"));
    assert!(detect::detect_captcha("reCAPTCHA verification"));
    assert!(detect::detect_captcha("Prove you are human"));
    assert!(!detect::detect_captcha("Normal text without verification"));
    assert!(!detect::detect_captcha("Login successful"));
}

#[test]
fn test_detect_error() {
    // Testa detecção de erros
    assert!(detect::detect_error("Error: something went wrong").is_some());
    assert!(detect::detect_error("Failed to connect").is_some());
    assert!(detect::detect_error("Access denied").is_some());
    assert!(detect::detect_error("Normal success message").is_none());
}

#[test]
fn test_compare_png_empty() {
    // Testa comparação com PNGs vazios/inválidos
    let empty: &[u8] = &[];
    let result = compare::compare_png(empty, empty);
    // Deve retornar erro, mas não deve panic
    assert!(result.is_err());
}

#[test]
fn test_ocr_text_empty() {
    // Testa OCR com bytes vazios
    let empty: &[u8] = &[];
    let result = ocr::ocr_text(empty);
    // Deve retornar string vazia, não deve panic
    assert_eq!(result, "");
}


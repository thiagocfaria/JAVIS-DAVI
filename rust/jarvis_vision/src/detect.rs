use once_cell::sync::Lazy;
use regex::Regex;

static CAPTCHA_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        Regex::new("captcha").unwrap(),
        Regex::new("recaptcha").unwrap(),
        Regex::new("hcaptcha").unwrap(),
        Regex::new("prove.*human").unwrap(),
        Regex::new("robot").unwrap(),
        Regex::new("nao.*robo").unwrap(),
        Regex::new("selecione.*imagens").unwrap(),
        Regex::new("select.*images").unwrap(),
        Regex::new("verify.*human").unwrap(),
    ]
});

static TWOFA_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        Regex::new("two.?factor").unwrap(),
        Regex::new("2fa").unwrap(),
        Regex::new("dois.*fatores").unwrap(),
        Regex::new("verification.*code").unwrap(),
        Regex::new("codigo.*verificacao").unwrap(),
        Regex::new("enter.*code").unwrap(),
        Regex::new("digite.*codigo").unwrap(),
        Regex::new("sms.*code").unwrap(),
        Regex::new("authenticator").unwrap(),
        Regex::new("autenticador").unwrap(),
    ]
});

static ERROR_PATTERNS: Lazy<Vec<(Regex, &'static str)>> = Lazy::new(|| {
    vec![
        (Regex::new("erro|error").unwrap(), "Error detected"),
        (Regex::new("falha|failed|failure").unwrap(), "Failure detected"),
        (Regex::new("nao.*encontrado|not.*found").unwrap(), "Not found"),
        (Regex::new("acesso.*negado|access.*denied").unwrap(), "Access denied"),
        (Regex::new("conexao.*perdida|connection.*lost").unwrap(), "Connection lost"),
        (Regex::new("tempo.*esgotado|timeout|timed.*out").unwrap(), "Timeout"),
        (Regex::new("invalido|invalid").unwrap(), "Invalid input"),
    ]
});

pub fn detect_captcha(text: &str) -> bool {
    let text = text.to_lowercase();

    for pattern in CAPTCHA_PATTERNS.iter().chain(TWOFA_PATTERNS.iter()) {
        if pattern.is_match(&text) {
            return true;
        }
    }

    false
}

pub fn detect_error(text: &str) -> Option<String> {
    let text = text.to_lowercase();

    for (pattern, message) in ERROR_PATTERNS.iter() {
        if pattern.is_match(&text) {
            return Some((*message).to_string());
        }
    }

    None
}

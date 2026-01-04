use std::env;

const BLOCKED_BANK_DOMAINS: [&str; 30] = [
    "nubank", "itau", "bradesco", "santander", "caixa", "bb.com.br",
    "bancodobrasil", "inter", "c6bank", "original", "safra", "btg",
    "banrisul", "sicoob", "sicredi", "banestes",
    "picpay", "mercadopago", "pagseguro", "pagbank", "ame",
    "paypal", "stripe", "wise", "revolut",
    "binance", "coinbase", "kraken", "ftx", "crypto.com",
];

const BLOCKED_APPS: [&str; 24] = [
    "1password", "bitwarden", "keepass", "keepassxc", "lastpass",
    "dashlane", "enpass",
    "nubank", "itau", "bradesco", "santander", "caixa", "bb",
    "inter", "c6bank", "picpay", "mercadopago",
    "metamask", "exodus", "ledger", "trezor",
    "gnome-keyring", "seahorse", "kwallet",
];

fn split_env(key: &str) -> Vec<String> {
    env::var(key)
        .unwrap_or_default()
        .split(',')
        .map(|item| item.trim().to_lowercase())
        .filter(|item| !item.is_empty())
        .collect()
}

fn blocked_domains() -> Vec<String> {
    let mut items: Vec<String> = BLOCKED_BANK_DOMAINS.iter().map(|s| s.to_string()).collect();
    items.extend(split_env("JARVIS_BLOCKED_DOMAINS"));
    items
}

fn blocked_apps() -> Vec<String> {
    let mut items: Vec<String> = BLOCKED_APPS.iter().map(|s| s.to_string()).collect();
    items.extend(split_env("JARVIS_BLOCKED_APPS"));
    items
}

pub fn is_screenshot_allowed(app_name: &str, url: &str) -> bool {
    let app_lower = app_name.to_lowercase();
    let url_lower = url.to_lowercase();

    for blocked in blocked_apps() {
        if !blocked.is_empty() && app_lower.contains(&blocked) {
            return false;
        }
    }

    for domain in blocked_domains() {
        if !domain.is_empty() && url_lower.contains(&domain) {
            return false;
        }
    }

    true
}

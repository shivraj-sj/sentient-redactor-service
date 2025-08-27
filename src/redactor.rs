use anyhow::{anyhow, Result};
use reqwest::Client;
use serde_json::{json, Value};
use std::time::Duration;
use tracing::info;

pub struct RedactorService {
    client: Client,
    presidio_url: String,
}

impl RedactorService {
    pub fn new() -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .expect("Failed to create HTTP client");

        let presidio_url = std::env::var("PRESIDIO_URL")
            .unwrap_or_else(|_| "http://localhost:8001".to_string());

        info!("RedactorService initialized with Presidio URL: {}", presidio_url);

        Self {
            client,
            presidio_url,
        }
    }

    pub async fn redact_text_with_strategy(&self, text: &str, strategy: &str) -> Result<String> {
        let response = self.client
            .post(&format!("{}/redact", self.presidio_url))
            .json(&json!({
                "text": text,
                "strategy": strategy
            }))
            .send()
            .await
            .map_err(|e| anyhow!("Presidio request failed: {}", e))?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            return Err(anyhow!("Presidio error ({}): {}", status, error_text));
        }

        let result: Value = response.json().await
            .map_err(|e| anyhow!("Failed to parse response: {}", e))?;

        let redacted_text = result["redacted_text"]
            .as_str()
            .ok_or_else(|| anyhow!("No redacted_text in response"))?;

        Ok(redacted_text.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_redactor_service() {
        let redactor = RedactorService::new();
        let text = "My name is John Doe and my email is john@example.com";
        let redacted = redactor.redact_text_with_strategy(text, "replace").await.unwrap();
        println!("Redacted: {}", redacted);
        assert!(!redacted.contains("John Doe"));
        assert!(!redacted.contains("john@example.com"));
        assert!(redacted.contains("<PERSON>"));
        assert!(redacted.contains("<EMAIL_ADDRESS>"));
    }
}

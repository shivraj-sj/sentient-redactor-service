use chacha20poly1305::{
    aead::{Aead, KeyInit},
    ChaCha20Poly1305, Key, Nonce,
};
use rsa::{
    RsaPrivateKey, RsaPublicKey,
    pkcs8::{EncodePublicKey, LineEnding},
    Oaep,
};
use sha2::Sha256;
use anyhow::{anyhow, Result};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use rand::rngs::OsRng;

pub struct CryptoService {
    private_key: RsaPrivateKey,
    public_key: RsaPublicKey,
}

impl CryptoService {
    pub fn new() -> Self {
        // Generate RSA key pair for session key encryption
        let mut rng = OsRng;
        let private_key = RsaPrivateKey::new(&mut rng, 2048)
            .expect("Failed to generate RSA private key");
        let public_key = RsaPublicKey::from(&private_key);
        
        Self {
            private_key,
            public_key,
        }
    }

    pub fn get_public_key(&self) -> Result<String> {
        // Export public key in PEM format
        let pem = self.public_key.to_public_key_pem(LineEnding::LF)
            .map_err(|e| anyhow!("Failed to export public key: {}", e))?;
        Ok(pem)
    }

    pub fn decrypt_session_key(&self, encrypted_session_key: &str) -> Result<Vec<u8>> {
        // Decode base64 encrypted session key
        let encrypted_bytes = BASE64.decode(encrypted_session_key)
            .map_err(|e| anyhow!("Invalid base64: {}", e))?;
        
        // Decrypt session key with RSA private key using OAEP padding
        let session_key = self.private_key.decrypt(
            Oaep::new::<Sha256>(),
            &encrypted_bytes
        ).map_err(|e| anyhow!("RSA decryption failed: {}", e))?;
        
        Ok(session_key)
    }

    pub fn decrypt_file_with_session_key(&self, encrypted_data: &str, session_key: &[u8]) -> Result<String> {
        // Use the session key to decrypt the file content
        let nonce_bytes = [0u8; 12]; // 96-bit nonce for ChaCha20-Poly1305
        let nonce = Nonce::from_slice(&nonce_bytes);
        
        // Create cipher with session key
        let key = Key::from_slice(session_key);
        let cipher = ChaCha20Poly1305::new(key);
        
        // Decode base64 encrypted data
        let decoded = BASE64.decode(encrypted_data)
            .map_err(|e| anyhow!("Invalid base64: {}", e))?;
        
        // Decrypt with session key
        let plaintext = cipher.decrypt(nonce, decoded.as_ref())
            .map_err(|e| anyhow!("Decryption failed: {}", e))?;
        
        String::from_utf8(plaintext)
            .map_err(|e| anyhow!("Invalid UTF-8: {}", e))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_public_key_export() {
        let crypto = CryptoService::new();
        let public_key = crypto.get_public_key().unwrap();
        
        // Verify it's a valid PEM format
        assert!(public_key.starts_with("-----BEGIN PUBLIC KEY-----"));
        assert!(public_key.ends_with("-----END PUBLIC KEY-----\n"));
    }

    #[test]
    fn test_file_encryption_decryption() {
        let crypto = CryptoService::new();
        let test_data = "Hello, World! This is a test message.";
        let session_key = [1u8; 32]; // 32-byte session key
        
        // Encrypt file data (simulate client side)
        let nonce_bytes = [0u8; 12];
        let nonce = Nonce::from_slice(&nonce_bytes);
        let key = Key::from_slice(&session_key);
        let cipher = ChaCha20Poly1305::new(key);
        
        let encrypted = cipher.encrypt(nonce, test_data.as_bytes()).unwrap();
        let encrypted_b64 = BASE64.encode(&encrypted);
        
        // Decrypt file data (server side)
        let decrypted = crypto.decrypt_file_with_session_key(&encrypted_b64, &session_key).unwrap();
        
        assert_eq!(test_data, decrypted);
    }
}

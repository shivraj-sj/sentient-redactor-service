use axum::{
    extract::State,
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn};
use uuid::Uuid;

mod crypto;
mod redactor;
mod storage;

use crypto::CryptoService;
use redactor::RedactorService;
use storage::FileStorage;

#[derive(Clone)]
struct AppState {
    crypto_service: Arc<CryptoService>,
    redactor_service: Arc<RedactorService>,
    file_storage: Arc<RwLock<FileStorage>>,
}

#[derive(Deserialize)]
struct UploadRequest {
    encrypted_data: String,
    encrypted_session_key: String,
    file_name: Option<String>,
    redaction_strategy: Option<String>,
}

#[derive(Serialize)]
struct UploadResponse {
    file_id: String,
    filename: String,
    message: String,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}



#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::fmt::init();

    info!("Starting Sentient TEE Redactor Service...");

    // Initialize services
    let crypto_service = Arc::new(CryptoService::new());
    let redactor_service = Arc::new(RedactorService::new());
    let file_storage = Arc::new(RwLock::new(FileStorage::new()));

    let state = AppState {
        crypto_service,
        redactor_service,
        file_storage,
    };


    // Build router
    let app = Router::new()
        .route("/health", get(health_check))
        .route("/handshake", get(handshake))
        .route("/upload", post(upload_file))
        .route("/download/:file_id", get(download_file))
        .with_state(state);

    // Start server
    let listener = tokio::net::TcpListener::bind("0.0.0.0:10003").await.unwrap();
    info!("Server listening on http://0.0.0.0:10003");

    axum::serve(listener, app).await.unwrap();
}

async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "healthy",
        "service": "sentient-tee-redactor"
    }))
}

async fn handshake(State(state): State<AppState>) -> impl IntoResponse {
    match state.crypto_service.get_public_key() {
        Ok(public_key) => {
            Json(serde_json::json!({
                "public_key": public_key,
                "algorithm": "RSA-2048"
            })).into_response()
        }
        Err(e) => {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Failed to get public key: {}", e),
                }),
            )
                .into_response()
        }
    }
}

async fn upload_file(
    State(state): State<AppState>,
    Json(payload): Json<UploadRequest>,
) -> impl IntoResponse {
    let file_id = Uuid::new_v4().to_string();
    
    info!("Processing upload for file_id: {}", file_id);

    // Decrypt the session key first
    let session_key = match state.crypto_service.decrypt_session_key(&payload.encrypted_session_key) {
        Ok(key) => key,
        Err(e) => {
            warn!("Session key decryption failed for file_id {}: {}", file_id, e);
            return (
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse {
                    error: format!("Session key decryption failed: {}", e),
                }),
            )
                .into_response();
        }
    };

    // Decrypt the file using the session key
    let decrypted_content = match state.crypto_service.decrypt_file_with_session_key(&payload.encrypted_data, &session_key) {
        Ok(content) => content,
        Err(e) => {
            warn!("File decryption failed for file_id {}: {}", file_id, e);
            return (
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse {
                    error: format!("File decryption failed: {}", e),
                }),
            )
                .into_response();
        }
    };

    // Perform redaction with optional strategy
    let strategy = payload.redaction_strategy.unwrap_or_else(|| "replace".to_string());
    let redacted_content = match state.redactor_service.redact_text_with_strategy(&decrypted_content, &strategy).await {
        Ok(content) => content,
        Err(e) => {
            warn!("Redaction failed for file_id {}: {}", file_id, e);
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Redaction failed: {}", e),
                }),
            )
                .into_response();
        }
    };

    // Store the redacted file
    let name = payload.file_name.as_deref().unwrap_or("file");
    let final_file_name = format!("{}_{}_redacted_{}.txt", name, strategy, file_id);
    {
        let mut storage = state.file_storage.write().await;
        storage.store_file(&file_id, &final_file_name, &redacted_content);
    }

    info!("Successfully processed file_id: {}", file_id);

    (
        StatusCode::OK,
        Json(UploadResponse {
            file_id,
            filename: final_file_name,
            message: "File uploaded and redacted successfully".to_string(),
        }),
    )
        .into_response()
}

async fn download_file(
    State(state): State<AppState>,
    axum::extract::Path(file_id): axum::extract::Path<String>,
) -> impl IntoResponse {
    let storage = state.file_storage.read().await;
    
    match storage.get_file(&file_id) {
        Some((file_name, content)) => {
            let mut headers = HeaderMap::new();
            headers.insert(
                "Content-Disposition",
                format!("attachment; filename=\"{}\"", file_name).parse().unwrap(),
            );
            headers.insert("Content-Type", "text/plain".parse().unwrap());
            
            (StatusCode::OK, headers, content).into_response()
        }
        None => {
            (
                StatusCode::NOT_FOUND,
                Json(ErrorResponse {
                    error: "File not found".to_string(),
                }),
            )
                .into_response()
        }
    }
}

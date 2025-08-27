# Sentient Redactor Service

A secure PII redaction service built with Rust and Axum that accepts encrypted files, decrypts them, performs PII redaction using Microsoft Presidio, and makes the redacted files available for download.

## Features

- **Secure File Encryption/Decryption**: ChaCha20-Poly1305 encryption with RSA key exchange
- **Advanced PII Redaction**: Microsoft Presidio integration with enhanced entity detection
- **Comprehensive PII Coverage**: Support for different entity types including international identifiers
- **Multiple Redaction Strategies**: 4 configurable redaction approaches
- **RESTful API**: Built with Axum for high-performance async operations
- **In-Memory Storage**: Temporary file storage with metadata tracking
- **Complete Test Suite**: Python test client with secure key exchange demonstration

## Architecture

The service consists of four main components:

1. **CryptoService**: Handles secure key exchange (RSA-2048) and file encryption/decryption (ChaCha20-Poly1305)
2. **RedactorService**: Performs PII detection and redaction using Microsoft Presidio with configurable strategies
3. **FileStorage**: Manages in-memory file storage with metadata
4. **PresidioService**: Python microservice providing enhanced PII detection capabilities with comprehensive entity coverage

### Security Protocol

The service implements a secure key exchange protocol:

1. **Handshake**: Client requests server's RSA public key
2. **Session Key Generation**: Client generates a random 32-byte session key
3. **Session Key Encryption**: Client encrypts session key with server's RSA public key
4. **File Encryption**: Client encrypts file content with ChaCha20-Poly1305 using session key
5. **Upload**: Client sends encrypted file + encrypted session key to server
6. **Decryption**: Server decrypts session key with RSA private key, then decrypts file
7. **Redaction**: Server performs PII redaction using Microsoft Presidio with configurable strategy
8. **Storage**: Redacted file is stored with unique ID for later retrieval

## API Endpoints

### Health Check
```
GET /health
```
Returns service health status.

### Handshake (Get Server Public Key)
```
GET /handshake
```
Returns the server's RSA public key for secure key exchange.

Response:
```json
{
  "algorithm": "RSA-2048",
  "public_key": "-----BEGIN PUBLIC KEY-----\n..."
}
```

### Upload and Redact File (Secure)
```
POST /upload
Content-Type: application/json

{
  "encrypted_data": "base64_encoded_chacha20_encrypted_content",
  "encrypted_session_key": "base64_encoded_rsa_encrypted_session_key",
  "file_name": "optional_filename.txt",
  "redaction_strategy": "optional_strategy_name"
}
```

**Available Strategies**: `replace`, `mask`, `fake`, `custom`

Response:
```json
{
  "file_id": "uuid_of_processed_file",
  "filename": "processed_filename.txt",
  "message": "File uploaded and redacted successfully"
}
```

### Download Redacted File
```
GET /download/{file_id}
```
Returns the redacted file as a downloadable attachment.

## Setup and Installation

### Prerequisites
- Rust 1.70+ and Cargo
- Python 3.9+ with pip
- macOS/Linux/Windows

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sentient-redactor-service
```

2. Set up Python virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Build the Rust service:
```bash
cargo build --release
```

4. Start the Presidio service:
```bash
source venv/bin/activate
python3 presidio_service.py &
```

5. Start the main service:
```bash
cargo run --release
```

The main service will start on `http://0.0.0.0:3000` and the Presidio service on `http://localhost:8001`.

## Usage Examples

### Using the Python Test Client (Recommended)

The provided test client demonstrates the complete secure workflow:

```bash
source venv/bin/activate
python3 test_client.py --file demo_employment_contract.txt --strategy replace --non-interactive
```

The test client performs:
1. **Handshake**: Retrieves server's RSA public key
2. **Session Key Generation**: Creates random 32-byte session key
3. **Secure Encryption**: Encrypts session key with RSA, file with ChaCha20-Poly1305
4. **Upload & Download**: Tests the complete secure workflow
5. **Verification**: Compares redacted output with expected results

### Using curl (Basic Example)

1. **Test the handshake:**
```bash
curl -s http://localhost:3000/handshake | jq .
```

2. **Test the health endpoint:**
```bash
curl -s http://localhost:3000/health | jq .
```

3. **Test different redaction strategies:**
```bash
# Test with default 'replace' strategy
curl -X POST http://localhost:8001/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, my name is John Doe", "strategy": "replace"}'

# Test with 'fake' strategy
curl -X POST http://localhost:8001/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, my name is John Doe", "strategy": "fake"}'

# Test with 'custom' strategy
curl -X POST http://localhost:8001/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, my name is John Doe", "strategy": "custom"}'
```

4. **Get available strategies:**
```bash
curl -s http://localhost:8001/strategies | jq .
```

## Enhanced PII Detection and Redaction

The service uses Microsoft Presidio with enhanced configuration for comprehensive PII detection, which can identify and redact **different entity types**:

### Core PII Entities
- **Personal Names**: `<PERSON>`
- **Email Addresses**: `<EMAIL_ADDRESS>`
- **Phone Numbers**: `<PHONE_NUMBER>`
- **Credit Card Numbers**: `<CREDIT_CARD>`
- **Social Security Numbers**: `<US_SSN>`
- **IP Addresses**: `<IP_ADDRESS>`
- **Addresses**: `<LOCATION>`
- **Dates**: `<DATE_TIME>`
- **URLs**: `<URL>`

### Enhanced Detection Features
- **Spacy NLP Engine**: Uses `en_core_web_sm` model for better language understanding
- **Comprehensive Entity List**: Detects 25+ entity types in a single pass
- **No Custom Patterns**: Leverages Presidio's community-maintained recognizers for better maintainability

### Redaction Strategies

The service supports **different redaction strategies** to meet various use cases:

#### 1. **`replace` Strategy (Default)**
- **Description**: Replaces PII with entity type tags
- **Example**: `"John Doe"` → `<PERSON>`
- **Use case**: When you want to know what type of PII was found
- **Format**: `<PERSON>`, `<EMAIL_ADDRESS>`, `<CREDIT_CARD>`, etc.

#### 2. **`mask` Strategy**
- **Description**: Replaces PII with asterisks
- **Example**: `"John Doe"` → `****`
- **Use case**: When you want to completely obscure the data
- **Format**: `****` for all entity types

#### 3. **`fake` Strategy**
- **Description**: Replaces PII with realistic fake data
- **Example**: `"John Doe"` → `"Alice Johnson"`
- **Use case**: When you need realistic-looking data for testing or development
- **Format**: Realistic names, emails, phone numbers, etc.

#### 4. **`custom` Strategy**
- **Description**: Replaces PII with custom redaction tags
- **Example**: `"John Doe"` → `[REDACTED_NAME]`
- **Use case**: When you want specific redaction labels
- **Format**: `[REDACTED_NAME]`, `[REDACTED_EMAIL]`, etc.


## Development

### Running Tests
```bash
# Rust tests
cargo test

# Python tests
source venv/bin/activate
python3 test_client.py --file demo_employment_contract.txt --strategy replace --non-interactive

```

### Running with Logging
```bash
RUST_LOG=debug cargo run
```

### Building for Production
```bash
cargo build --release
```

### Stopping Services
```bash
# Stop the main service
pkill -f "cargo run"

# Stop the Presidio service
pkill -f "presidio_service.py"
```

## Security Considerations
- **End-to-End Encryption**: Files are encrypted client-side before transmission
- **Key Exchange**: Secure RSA-2048 key exchange protocol
- **Session Keys**: Unique session keys for each file upload
- **In-Memory Storage**: Files are stored temporarily in memory only
- **No Persistent Storage**: Redacted files are not permanently stored

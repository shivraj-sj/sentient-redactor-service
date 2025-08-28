#!/usr/bin/env python3
"""
CLI client for the Sentient TEE Redactor Service with RSA Key Exchange
"""

import requests
import base64
import json
import sys
import argparse
import re
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import os

# ANSI color codes for highlighting
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_colored(text, color=Colors.END):
    """Print colored text"""
    print(f"{color}{text}{Colors.END}")

def highlight_redacted_content(content, original_filename=None):
    """Highlight redacted portions by comparing with original file"""
    if not original_filename:
        print_colored("\n📄 Redacted content:", Colors.CYAN)
        print(content)
        return 0
    
    try:
        # Read the original file
        with open(original_filename, 'r') as f:
            original_content = f.read()
        
        # Common redaction patterns to identify what was redacted
        redaction_patterns = [
            r'<[^>]+>',  # <PERSON>, <LOCATION>, etc.
            r'\*{2,}',   # ****, ***, etc.
            r'\[REDACTED\].*?\[/REDACTED\]',  # [REDACTED]...[/REDACTED]
            r'<REDACTED>.*?</REDACTED>',      # <REDACTED>...</REDACTED>
            r'\{REDACTED\}.*?\{/REDACTED\}',  # {REDACTED}...{/REDACTED}
            r'\[MASKED\].*?\[/MASKED\]',      # [MASKED]...[/MASKED]
            r'<MASKED>.*?</MASKED>',          # <MASKED>...</MASKED>
            r'\[FAKE\].*?\[/FAKE\]',          # [FAKE]...[/FAKE]
            r'<FAKE>.*?</FAKE>',              # <FAKE>...</FAKE>
            r'\[REPLACE\].*?\[/REPLACE\]',    # [REPLACE]...[/REPLACE]
            r'<REPLACE>.*?</REPLACE>',        # <REPLACE>...</REPLACE>
        ]
        
        # Find all redacted portions
        redacted_positions = set()
        for pattern in redaction_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                redacted_positions.add((match.start(), match.end()))
        
        if redacted_positions:
            print_colored(f"\n📄 Redacted content (highlighted changes):", Colors.CYAN + Colors.BOLD)
            print_colored("=" * 60, Colors.CYAN)
            
            # Output the content with highlighting
            last_end = 0
            highlighted_content = ""
            
            for start, end in sorted(redacted_positions):
                # Add non-redacted text in green
                if start > last_end:
                    highlighted_content += f"{Colors.GREEN}{content[last_end:start]}{Colors.END}"
                
                # Add redacted text in red
                highlighted_content += f"{Colors.RED}{Colors.BOLD}{content[start:end]}{Colors.END}"
                last_end = end
            
            # Add any remaining non-redacted text
            if last_end < len(content):
                highlighted_content += f"{Colors.GREEN}{content[last_end:]}{Colors.END}"
            
            print(highlighted_content)
            print_colored("=" * 60, Colors.CYAN)
            print_colored(f"🔍 {len(redacted_positions)} redacted sections found (highlighted in red)", Colors.YELLOW)
            return len(redacted_positions)
        else:
            print_colored("\n📄 Redacted content:", Colors.CYAN)
            print_colored(content, Colors.GREEN)
            print_colored("✅ No redactions found - files are identical", Colors.GREEN)
            return 0
            
    except FileNotFoundError:
        print_colored(f"\n❌ Original file not found: {original_filename}", Colors.RED)
        print_colored("📄 Redacted content:", Colors.CYAN)
        print_colored(content, Colors.GREEN)
        return 0
    except Exception as e:
        print_colored(f"\n❌ Error comparing files: {e}", Colors.RED)
        print_colored("📄 Redacted content:", Colors.CYAN)
        print_colored(content, Colors.GREEN)
        return 0

def get_user_input(prompt, default=None, choices=None):
    """Get user input with optional default and choices"""
    if choices:
        prompt += f" ({'/'.join(choices)})"
    if default:
        prompt += f" [default: {default}]"
    prompt += ": "
    
    while True:
        user_input = input(prompt).strip()
        if not user_input and default:
            return default
        if choices and user_input not in choices:
            print_colored(f"Please choose from: {', '.join(choices)}", Colors.YELLOW)
            continue
        return user_input

def test_handshake(base_url):
    """Test the handshake endpoint to get server's public key"""
    print_colored("Testing handshake...", Colors.CYAN)
    try:
        response = requests.get(f"{base_url}/handshake")
        if response.status_code == 200:
            result = response.json()
            print_colored("✅ Handshake successful", Colors.GREEN)
            print_colored(f"Algorithm: {result['algorithm']}", Colors.GREEN)
            print_colored(f"Public key length: {len(result['public_key'])} characters", Colors.GREEN)
            return result['public_key']
        else:
            print_colored(f"❌ Handshake failed: {response.status_code}", Colors.RED)
            print_colored(f"Error: {response.text}", Colors.RED)
            return None
    except Exception as e:
        print_colored(f"❌ Handshake error: {e}", Colors.RED)
        return None

def generate_session_key():
    """Generate a random 32-byte session key for ChaCha20-Poly1305"""
    return os.urandom(32)

def encrypt_session_key(session_key, server_public_key_pem):
    """Encrypt session key with RSA public key"""
    # Load server's RSA public key
    public_key = serialization.load_pem_public_key(server_public_key_pem.encode())
    
    # Encrypt the session key with RSA using OAEP padding
    encrypted_key = public_key.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    return base64.b64encode(encrypted_key).decode('utf-8')

def encrypt_file_with_session_key(file_content, session_key):
    """Encrypt file content with ChaCha20-Poly1305 using session key"""
    # Create ChaCha20-Poly1305 cipher
    cipher = ChaCha20Poly1305(session_key)
    
    # Use a fixed nonce for this prototype (in production, use random nonce)
    nonce = b'\x00' * 12
    
    # Encrypt the file content
    encrypted_data = cipher.encrypt(nonce, file_content.encode('utf-8'), None)
    
    return base64.b64encode(encrypted_data).decode('utf-8')

def test_secure_upload(base_url, server_public_key, filename, strategy="replace"):
    """Test secure file upload with proper key exchange"""
    print_colored(f"\nTesting secure file upload with key exchange for file: {filename}", Colors.CYAN)
    
    # Read test data from specified file
    try:
        with open(filename, 'r') as f:
            test_content = f.read()
        print_colored(f"✅ Loaded {filename} ({len(test_content)} characters)", Colors.GREEN)
    except FileNotFoundError:
        print_colored(f"❌ {filename} not found", Colors.RED)
        return None
    
    try:
        # Step 1: Generate session key
        session_key = generate_session_key()
        print_colored(f"✅ Generated session key: {len(session_key)} bytes", Colors.GREEN)
        
        # Step 2: Encrypt session key with server's public key
        encrypted_session_key = encrypt_session_key(session_key, server_public_key)
        print_colored(f"✅ Encrypted session key with RSA", Colors.GREEN)
        
        # Step 3: Encrypt file content with session key
        encrypted_file_data = encrypt_file_with_session_key(test_content, session_key)
        print_colored(f"✅ Encrypted file content with ChaCha20-Poly1305", Colors.GREEN)
        
        # Step 4: Upload encrypted data
        # Remove extension from filename for server
        name_without_ext = filename
        if '.' in filename:
            name_without_ext = filename.rsplit('.', 1)[0]
        
        payload = {
            "encrypted_data": encrypted_file_data,
            "encrypted_session_key": encrypted_session_key,
            "file_name": name_without_ext,
            "redaction_strategy": strategy
        }
        
        response = requests.post(
            f"{base_url}/upload",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            file_id = result["file_id"]
            filename = result["filename"]
            print_colored("✅ Secure upload successful", Colors.GREEN)
            print_colored(f"File ID: {file_id}", Colors.GREEN)
            print_colored(f"Filename: {filename}", Colors.GREEN)
            print_colored(f"Message: {result['message']}", Colors.GREEN)
            return file_id, filename
        else:
            print_colored(f"❌ Upload failed: {response.status_code}", Colors.RED)
            print_colored(f"Error: {response.text}", Colors.RED)
            return None
            
    except Exception as e:
        print_colored(f"❌ Upload error: {e}", Colors.RED)
        return None

def download_file(base_url, file_id, filename=None):
    """Download the redacted file from server"""
    if not file_id:
        print_colored("❌ No file ID provided for download", Colors.RED)
        return None
    
    print_colored(f"\nDownloading redacted file for ID: {file_id}", Colors.CYAN)
    
    try:
        response = requests.get(f"{base_url}/download/{file_id}")
        
        if response.status_code == 200:
            print_colored("✅ File downloaded successfully", Colors.GREEN)
            
            # Use the filename from server response or generate a default
            if not filename:
                filename = f"redacted_{file_id}.txt"
            
            with open(filename, "wb") as f:
                f.write(response.content)
            
            print_colored(f"Redacted file saved as: {filename}", Colors.GREEN)
            return filename
        else:
            print_colored(f"❌ Download failed: {response.status_code}", Colors.RED)
            print_colored(f"Error: {response.text}", Colors.RED)
            return None
            
    except Exception as e:
        print_colored(f"❌ Download error: {e}", Colors.RED)
        return None

def verify_redaction(filename, expected_file):
    """Verify redaction by comparing with expected file"""
    if not filename:
        print_colored("❌ No filename provided for verification", Colors.RED)
        return False
    
    print_colored(f"\nVerifying redaction in file: {filename}", Colors.CYAN)
    print_colored(f"Comparing against expected file: {expected_file}", Colors.CYAN)
    
    try:
        # Read the redacted file
        with open(filename, 'r') as f:
            redacted_content = f.read()
        
        # Read the expected redacted content
        with open(expected_file, 'r') as f:
            expected_content = f.read()
        
        # Compare word by word
        redacted_words = redacted_content.split()
        expected_words = expected_content.split()
        
        print_colored(f"Comparing {len(redacted_words)} words with {len(expected_words)} expected words", Colors.CYAN)
        
        # Check if lengths match
        if len(redacted_words) != len(expected_words):
            print_colored(f"❌ Word count mismatch: {len(redacted_words)} vs {len(expected_words)}", Colors.RED)
            return False
        
        # Compare each word
        mismatches = []
        for i, (redacted_word, expected_word) in enumerate(zip(redacted_words, expected_words)):
            if redacted_word != expected_word:
                mismatches.append((i, redacted_word, expected_word))
        
        if mismatches:
            print_colored(f"❌ Found {len(mismatches)} word mismatches:", Colors.RED)
            for i, redacted, expected in mismatches[:5]:  # Show first 5 mismatches
                print_colored(f"   Word {i}: '{redacted}' != '{expected}'", Colors.RED)
            if len(mismatches) > 5:
                print_colored(f"   ... and {len(mismatches) - 5} more", Colors.YELLOW)
            return False
        else:
            print_colored("✅ All words match perfectly!", Colors.GREEN)
            return True
            
    except FileNotFoundError as e:
        print_colored(f"❌ File not found: {e}", Colors.RED)
        return False
    except Exception as e:
        print_colored(f"❌ Verification error: {e}", Colors.RED)
        return False

def list_available_files():
    """List available files in current directory"""
    txt_files = list(Path('.').glob('*.txt'))
    if txt_files:
        return txt_files
    else:
        print_colored("No .txt files found in current directory", Colors.YELLOW)
        return []

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Sentient TEE Redactor CLI Client')
    parser.add_argument('--url', default='http://localhost:10003', 
                       help='Base URL of the redactor service (default: http://localhost:10003)')
    parser.add_argument('--file', help='File to be redacted')
    parser.add_argument('--strategy', choices=['replace', 'mask', 'fake'], default='replace',
                       help='Redaction strategy (default: replace)')
    parser.add_argument('--non-interactive', action='store_true',
                       help='Run in non-interactive mode (use command line arguments only)')
    
    args = parser.parse_args()
    base_url = args.url
    
    print_colored("🔐 Sentient TEE Redactor CLI Client", Colors.BOLD + Colors.CYAN)
    print_colored("=" * 50, Colors.CYAN)
    
    # Test handshake
    server_public_key = test_handshake(base_url)
    if not server_public_key:
        print_colored("❌ Cannot proceed without server public key", Colors.RED)
        sys.exit(1)
    
    # Get file to redact
    if args.file:
        filename = args.file
        if not Path(filename).exists():
            print_colored(f"❌ File not found: {filename}", Colors.RED)
            sys.exit(1)
    else:
        if args.non_interactive:
            print_colored("❌ File must be specified in non-interactive mode", Colors.RED)
            sys.exit(1)
        
        # List available files
        available_files = list_available_files()
        if not available_files:
            print_colored("Please provide a file path:", Colors.CYAN)
            filename = get_user_input("File path")
        else:
            print_colored("\nSelect a file to redact:", Colors.CYAN)
            for i, file in enumerate(available_files, 1):
                print_colored(f"  {i}. {file.name}", Colors.BLUE)
            print_colored(f"  {len(available_files) + 1}. Enter custom path", Colors.BLUE)
            
            choice = get_user_input("Choice", choices=[str(i) for i in range(1, len(available_files) + 2)])
            
            if int(choice) <= len(available_files):
                filename = available_files[int(choice) - 1].name
            else:
                filename = get_user_input("Custom file path")
    
    # Get redaction strategy
    if args.non_interactive:
        strategy = args.strategy
    else:
        strategy = get_user_input("Redaction strategy", default="replace", 
                                choices=["replace", "mask", "fake"])
    
    # Upload file
    result = test_secure_upload(base_url, server_public_key, filename, strategy)
    if not result:
        print_colored("❌ Upload failed", Colors.RED)
        sys.exit(1)
    
    file_id, server_filename = result
    
    # Ask if user wants to download
    if args.non_interactive:
        download_choice = "y"
    else:
        download_choice = get_user_input("Download redacted file?", default="y", choices=["y", "n"])
    
    if download_choice.lower() == "y":
        downloaded_filename = download_file(base_url, file_id, server_filename)
        if not downloaded_filename:
            print_colored("❌ Download failed", Colors.RED)
            sys.exit(1)
        
        # Highlight redacted portions
        try:
            with open(downloaded_filename, 'r') as f:
                content = f.read()
            highlight_redacted_content(content, filename) # Pass original filename for comparison
        except Exception as e:
            print_colored(f"❌ Error reading downloaded file: {e}", Colors.RED)
        
        # Ask if verification is needed
        if args.non_interactive:
            verify_choice = "n"
        else:
            verify_choice = get_user_input("Verify redaction against expected file?", default="n", choices=["y", "n"])
        
        if verify_choice.lower() == "y":
            # Look for expected file
            expected_files = list(Path('.').glob('*_anonymized.txt'))
            expected_files.extend(list(Path('.').glob('*_redacted.txt')))
            
            if expected_files:
                print_colored("\nAvailable expected files:", Colors.CYAN)
                for i, file in enumerate(expected_files, 1):
                    print_colored(f"  {i}. {file.name}", Colors.BLUE)
                print_colored(f"  {len(expected_files) + 1}. Enter custom path", Colors.BLUE)
                
                choice = get_user_input("Select expected file", 
                                      choices=[str(i) for i in range(1, len(expected_files) + 2)])
                
                if int(choice) <= len(expected_files):
                    expected_file = expected_files[int(choice) - 1].name
                else:
                    expected_file = get_user_input("Custom expected file path")
            else:
                expected_file = get_user_input("Expected file path")
            
            if verify_redaction(downloaded_filename, expected_file):
                print_colored("\n🎉 Verification completed successfully!", Colors.GREEN + Colors.BOLD)
            else:
                print_colored("\n❌ Verification failed", Colors.RED)
    
    print_colored("\n✨ CLI session completed!", Colors.GREEN + Colors.BOLD)

if __name__ == "__main__":
    main()
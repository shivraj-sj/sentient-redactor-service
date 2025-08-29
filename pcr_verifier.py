#!/usr/bin/env python3
"""
Simple PCR Verifier for AWS Nitro Enclaves
"""

import requests
import json
import os
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def load_pcrs_from_file(filename: str) -> dict:
    """Load expected PCRs from JSON file"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            print_colored(f"✅ Successfully loaded {data} from {filename}", Colors.GREEN)
        return data.get('pcrs', {})
    except Exception as e:
        print_colored(f"Error loading PCRs from {filename}: {e}", Colors.RED)
        return {}

def get_pcrs_from_server(server_url: str) -> dict:
    """Get current PCRs from attestation server using verify_pcrs endpoint"""
    try:
        print_colored("🔍 Fetching PCRs from attestation server...", Colors.CYAN)
        print_colored("⚠️  SSL verification disabled for self-signed certificates", Colors.YELLOW)
        
        # Send empty PCRs to get actual PCRs from server
        # Disable SSL verification for self-signed certificates in development
        response = requests.post(f"{server_url}/verify_pcrs/", 
                               json={"pcrs": ""}, 
                               timeout=10,
                               verify=False)
        
        if response.status_code == 200:
            # Extract PCRs from response text
            text = response.text
            if "PCRs retrieved from enclave's attestation document:" in text:
                # Find PCRs section and parse
                start = text.find("PCRs retrieved from enclave's attestation document:") + 47
                end = text.find("\n", start)
                pcrs_text = text[start:end].strip()
                
                # Debug: show the raw PCR text
                print_colored(f"🔍 Raw PCR text: {repr(pcrs_text)}", Colors.BLUE)
                
                # Parse the PCR text - it starts with 'ent: "0: ...' format
                pcrs = {}
                
                # Remove the 'ent: "' prefix and trailing '"'
                if pcrs_text.startswith('ent: "') and pcrs_text.endswith('"'):
                    pcrs_text = pcrs_text[6:-1]  # Remove 'ent: "' and '"'
                
                # Replace escaped newlines with actual newlines and clean up
                pcrs_text_clean = pcrs_text.replace('\\n', '\n').replace('\n', ' ').replace('  ', ' ')
                
                # Split by comma and parse each PCR
                for pair in pcrs_text_clean.split(','):
                    pair = pair.strip()
                    if ':' in pair:
                        parts = pair.split(':', 1)
                        if len(parts) == 2:
                            num = parts[0].strip()
                            value = parts[1].strip()
                            # Remove any quotes from the value
                            value = value.strip('"')
                            pcrs[num] = value
                
                print_colored(f"✅ Successfully retrieved {len(pcrs)} PCRs", Colors.GREEN)
                return pcrs
            else:
                print_colored("❌ PCRs not found in server response", Colors.RED)
                return {}
        else:
            print_colored(f"❌ Server error: {response.status_code}", Colors.RED)
            return {}
    except Exception as e:
        print_colored(f"❌ Error getting PCRs from server: {e}", Colors.RED)
        return {}

def verify_pcrs(expected: dict, actual: dict) -> bool:
    """Verify that expected PCRs match actual PCRs"""
    if not expected or not actual:
        return False
    
    print_colored("\n🔐 Verifying PCRs...", Colors.CYAN)
    print_colored("=" * 40, Colors.CYAN)
    
    mismatches = []
    for pcr_num, expected_value in expected.items():
        if pcr_num not in actual:
            print_colored(f"❌ PCR {pcr_num}: Not found in actual PCRs", Colors.RED)
            mismatches.append((pcr_num, expected_value, "NOT_FOUND"))
        elif actual[pcr_num] != expected_value:
            print_colored(f"❌ PCR {pcr_num}: Mismatch", Colors.RED)
            print_colored(f"   Expected: {expected_value}", Colors.YELLOW)
            print_colored(f"   Actual:   {actual[pcr_num]}", Colors.YELLOW)
            mismatches.append((pcr_num, expected_value, actual[pcr_num]))
        else:
            print_colored(f"✅ PCR {pcr_num}: Match", Colors.GREEN)
    
    if mismatches:
        print_colored(f"\n❌ Verification FAILED: {len(mismatches)} mismatches found", Colors.RED + Colors.BOLD)
        return False
    else:
        print_colored(f"\n✅ Verification PASSED: All {len(expected)} PCRs match", Colors.GREEN + Colors.BOLD)
        return True

def print_pcrs_summary(expected: dict, actual: dict):
    """Print a summary of PCRs comparison"""
    print_colored("\n📊 PCR Summary", Colors.BOLD + Colors.CYAN)
    print_colored("=" * 30, Colors.CYAN)
    
    print_colored(f"Expected PCRs: {len(expected)}", Colors.BLUE)
    print_colored(f"Actual PCRs:   {len(actual)}", Colors.BLUE)
    
    if expected and actual:
        print_colored("\nExpected PCRs:", Colors.YELLOW)
        for pcr_num, value in expected.items():
            print_colored(f"  PCR {pcr_num}: {value}", Colors.YELLOW)
        
        print_colored("\nActual PCRs:", Colors.GREEN)
        for pcr_num, value in actual.items():
            print_colored(f"  PCR {pcr_num}: {value}", Colors.GREEN)
def main():
    """Main function to load, fetch, and verify PCRs"""
    server_url = "https://localhost:8443"
    pcr_file = "expected_pcrs.json"
    
    print_colored("🔐 PCR Verification for AWS Nitro Enclaves", Colors.BOLD + Colors.CYAN)
    print_colored("=" * 50, Colors.CYAN)
    
    # Load expected PCRs
    print_colored("\n📁 Loading expected PCRs...", Colors.CYAN)
    expected_pcrs = load_pcrs_from_file(pcr_file)
    if not expected_pcrs:
        print_colored("❌ No expected PCRs loaded", Colors.RED)
        return
    
    print_colored(f"✅ Loaded {len(expected_pcrs)} expected PCRs from {pcr_file}", Colors.GREEN)
    
    # Get current PCRs from server
    current_pcrs = get_pcrs_from_server(server_url)
    if not current_pcrs:
        print_colored("❌ Failed to get PCRs from server", Colors.RED)
        return
    
    # Print summary
    print_pcrs_summary(expected_pcrs, current_pcrs)
    
    # Verify PCRs
    if verify_pcrs(expected_pcrs, current_pcrs):
        print_colored("\n🎉 PCR verification completed successfully!", Colors.GREEN + Colors.BOLD)
    else:
        print_colored("\n💥 PCR verification failed!", Colors.RED + Colors.BOLD)

if __name__ == "__main__":
    main()

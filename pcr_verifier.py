#!/usr/bin/env python3
"""
Simple PCR Verifier for AWS Nitro Enclaves
"""

import requests
import json
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
        
        # Send empty PCRs to get actual PCRs from server
        response = requests.post(f"{server_url}/verify_pcrs/", 
                               json={"pcrs": ""}, 
                               timeout=10)
        
        if response.status_code == 200:
            # Extract PCRs from response text
            text = response.text
            if "PCRs retrieved from enclave's attestation document:" in text:
                # Find PCRs section and parse
                start = text.find("PCRs retrieved from enclave's attestation document:") + 47
                end = text.find("\n", start)
                pcrs_text = text[start:end].strip()
                
                # Parse "0: hexvalue, 1: hexvalue" format
                pcrs = {}
                for pair in pcrs_text.split(','):
                    if ':' in pair:
                        num, value = pair.strip().split(':', 1)
                        pcrs[num.strip()] = value.strip()
                
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
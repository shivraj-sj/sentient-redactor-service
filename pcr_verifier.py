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



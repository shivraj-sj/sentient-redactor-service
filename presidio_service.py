#!/usr/bin/env python3
"""
Enhanced Presidio PII Service with multiple redaction strategies
"""

from flask import Flask, request, jsonify
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import RecognizerResult, OperatorConfig
from presidio_anonymizer.core.text_replace_builder import TextReplaceBuilder
from presidio_analyzer.nlp_engine import NlpEngineProvider
import random
import string

app = Flask(__name__)

# Configure NLP engine with better language support
nlp_configuration = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]
}

provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
nlp_engine = provider.create_engine()

# Initialize Presidio with enhanced configuration
analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
anonymizer = AnonymizerEngine()

# Sample fake data for replacement
FAKE_NAMES = ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Emma Brown", "Frank Miller"]
FAKE_EMAILS = ["user1@example.com", "user2@example.com", "user3@example.com", "user4@example.com"]
FAKE_PHONES = ["555-0101", "555-0102", "555-0103", "555-0104"]
FAKE_CREDIT_CARDS = ["4111-1111-1111-1111", "4222-2222-2222-2222", "4333-3333-3333-3333"]
FAKE_ADDRESSES = ["123 Main St", "456 Oak Ave", "789 Pine Rd", "321 Elm St"]
FAKE_CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
FAKE_STATES = ["NY", "CA", "IL", "TX", "AZ"]

def generate_random_string(length=8):
    """Generate a random string of specified length"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_anonymization_config(strategy="replace"):
    """
    Get anonymization configuration based on strategy
    Available strategies:
    - 'replace': Replace with entity type tags (e.g., <PERSON>)
    - 'mask': Replace with asterisks (e.g., ****)
    - 'fake': Replace with realistic fake data
    - 'custom': Replace with custom text
    """
    
    if strategy == "replace":
        # Default Presidio behavior - replace with entity tags
        return {}
    
    elif strategy == "mask":
        # Replace with asterisks (simplified)
        return {
            "PERSON": OperatorConfig("replace", {"new_value": "****"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "****"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "****"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "****"}),
            "US_SSN": OperatorConfig("replace", {"new_value": "****"}),
            "IP_ADDRESS": OperatorConfig("replace", {"new_value": "****"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "****"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "****"}),
            "URL": OperatorConfig("replace", {"new_value": "****"}),
        }
    
    elif strategy == "fake":
        # Replace with realistic fake data
        return {
            "PERSON": OperatorConfig("replace", {"new_value": random.choice(FAKE_NAMES)}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": random.choice(FAKE_EMAILS)}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": random.choice(FAKE_PHONES)}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": random.choice(FAKE_CREDIT_CARDS)}),
            "US_SSN": OperatorConfig("replace", {"new_value": "123-45-6789"}),
            "IP_ADDRESS": OperatorConfig("replace", {"new_value": "192.168.1.1"}),
            "LOCATION": OperatorConfig("replace", {"new_value": f"{random.choice(FAKE_CITIES)}, {random.choice(FAKE_STATES)}"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "2023-01-01"}),
            "URL": OperatorConfig("replace", {"new_value": "https://example.com"}),
        }
    
    elif strategy == "custom":
        # Replace with custom text
        return {
            "PERSON": OperatorConfig("replace", {"new_value": "[REDACTED_NAME]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[REDACTED_EMAIL]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[REDACTED_PHONE]"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[REDACTED_CREDIT_CARD]"}),
            "US_SSN": OperatorConfig("replace", {"new_value": "[REDACTED_SSN]"}),
            "IP_ADDRESS": OperatorConfig("replace", {"new_value": "[REDACTED_IP]"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "[REDACTED_LOCATION]"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "[REDACTED_DATE]"}),
            "URL": OperatorConfig("replace", {"new_value": "[REDACTED_URL]"}),
        }
    
    else:
        # Default to replace strategy
        return {}

@app.route('/redact', methods=['POST'])
def redact():
    """Redact PII using configurable redaction strategy"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        strategy = data.get('strategy', 'replace')  # Default to replace strategy
        
        # Comprehensive list of entities to detect
        entities_to_detect = [
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN", 
            "IP_ADDRESS", "LOCATION", "DATE_TIME", "URL", "US_DRIVER_LICENSE",
            "US_PASSPORT", "UK_NHS", "US_BANK_NUMBER", "NRP", "MEDICAL_LICENSE",
            "US_ITIN", "US_DEA", "US_NPI", "AU_ABN", "AU_ACN", "AU_TFN", "AU_MEDICARE",
            "CA_CPP", "CA_SIN", "IN_AADHAAR", "IN_PAN", "SG_NRIC", "ZA_ID", "PL_PESEL"
        ]
        
        # Analyze the text with comprehensive entity detection
        results = analyzer.analyze(
            text=text, 
            language="en",
            entities=entities_to_detect,
            score_threshold=0.3  # Lower threshold to catch more entities
        )
        
        # Get anonymization configuration based on strategy
        anonymization_config = get_anonymization_config(strategy)
        
        # Anonymize with the specified strategy
        if anonymization_config:
            anonymized = anonymizer.anonymize(
                text=text, 
                analyzer_results=results,
                operators=anonymization_config
            )
        else:
            # Use default Presidio behavior
            anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
        
        return jsonify({
            "redacted_text": anonymized.text,
            "strategy_used": strategy,
            "entities_found": [result.entity_type for result in results],
            "entity_details": [
                {
                    "entity_type": result.entity_type,
                    "start": result.start,
                    "end": result.end,
                    "score": result.score,
                    "text": text[result.start:result.end]
                }
                for result in results
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/strategies', methods=['GET'])
def get_strategies():
    """Get available redaction strategies"""
    strategies = {
        "replace": {
            "description": "Replace with entity type tags (e.g., <PERSON>, <EMAIL_ADDRESS>)",
            "example": "John Doe → <PERSON>"
        },
        "mask": {
            "description": "Replace with asterisks (e.g., ****)",
            "example": "John Doe → ********"
        },
        "fake": {
            "description": "Replace with realistic fake data",
            "example": "John Doe → Alice Johnson"
        },
        "custom": {
            "description": "Replace with custom redaction tags",
            "example": "John Doe → [REDACTED_NAME]"
        }
    }
    return jsonify({"available_strategies": strategies})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8001)

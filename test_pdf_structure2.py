"""
Test to see the exact structure of the PDF response - BETTER VERSION
"""

import requests
import json
import base64

# Credentials
API_KEY = "5a959ce1aad74eea90a95cbc700bf32b"
COMPANY_ID = "999630747_acs"
COMPANY_PASSWORD = "SBBEm7T9"
USER_ID = "apiRouS"
USER_PASSWORD = "NJgXeHkL"

BASE_URL = "https://webservices.acscourier.net/ACSRestServices/api/ACSAutoRest"

voucher_no = "7401461340"

payload = {
    "ACSAlias": "ACS_Print_Voucher_V2",
    "ACSInputParameters": {
        "Company_ID": COMPANY_ID,
        "Company_Password": COMPANY_PASSWORD,
        "User_ID": USER_ID,
        "User_Password": USER_PASSWORD,
        "Voucher_No": voucher_no,
        "Print_Type": 2,
        "Start_Position": 1,
        "Language": "GR"
    }
}

headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'Accept': 'application/json',
    'AcsApiKey': API_KEY
}

response = requests.post(BASE_URL, json=payload, headers=headers, timeout=30)
data = response.json()

print("="*70)
print("DETAILED STRUCTURE ANALYSIS")
print("="*70)

output_response = data.get('ACSOutputResponce', {})
value_output = output_response.get('ACSValueOutput', [])

print(f"\nACSValueOutput: {type(value_output)} with {len(value_output)} elements")

if value_output and len(value_output) > 0:
    first_item = value_output[0]
    print(f"\nFirst item type: {type(first_item)}")
    print(f"First item repr: {repr(first_item)[:200]}...")
    
    if isinstance(first_item, dict):
        print(f"\nKeys: {list(first_item.keys())}")
        
        for key in first_item.keys():
            value = first_item[key]
            print(f"\n--- Key: '{key}' ---")
            print(f"Value type: {type(value)}")
            
            if isinstance(value, dict):
                print(f"Dict keys: {list(value.keys())}")
                
                # Check each key in the nested dict
                for nested_key in value.keys():
                    nested_value = value[nested_key]
                    print(f"\n  Nested key: '{nested_key}'")
                    print(f"  Nested value type: {type(nested_value)}")
                    
                    if isinstance(nested_value, str):
                        print(f"  String length: {len(nested_value)}")
                        print(f"  First 100 chars: {nested_value[:100]}")
                        
                        # Try to decode
                        try:
                            decoded = base64.b64decode(nested_value)
                            print(f"  ✅ Successfully decoded! {len(decoded)} bytes")
                            print(f"  First 20 bytes: {decoded[:20]}")
                            
                            if decoded.startswith(b'%PDF'):
                                print(f"  ✅✅✅ THIS IS A VALID PDF!")
                                
                                # Save it
                                import os
                                os.makedirs('test_pdfs', exist_ok=True)
                                with open(f'test_pdfs/WORKING_{voucher_no}.pdf', 'wb') as f:
                                    f.write(decoded)
                                print(f"  ✅ Saved to test_pdfs/WORKING_{voucher_no}.pdf")
                        except Exception as e:
                            print(f"  ❌ Decode failed: {e}")

print("\n" + "="*70)


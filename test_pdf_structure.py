"""
Test to see the exact structure of the PDF response
"""

import requests
import json

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
print("RESPONSE STRUCTURE ANALYSIS")
print("="*70)

output_response = data.get('ACSOutputResponce', {})
value_output = output_response.get('ACSValueOutput', [])

print(f"\nACSValueOutput type: {type(value_output)}")
print(f"ACSValueOutput length: {len(value_output)}")

if value_output:
    print(f"\nFirst element type: {type(value_output[0])}")
    print(f"First element: {value_output[0]}")
    
    if isinstance(value_output[0], dict):
        print(f"\nKeys in first element: {list(value_output[0].keys())}")
        
        for key, value in value_output[0].items():
            print(f"\nKey: '{key}' (type: {type(key)})")
            print(f"Value type: {type(value)}")
            print(f"Value length: {len(str(value))}")
            if isinstance(value, str):
                print(f"First 100 chars: {value[:100]}")
                print(f"Last 50 chars: {value[-50:]}")
                
                # Try to decode as base64
                try:
                    import base64
                    decoded = base64.b64decode(value)
                    print(f"\nDecoded length: {len(decoded)} bytes")
                    print(f"First 20 bytes: {decoded[:20]}")
                    
                    if decoded.startswith(b'%PDF'):
                        print("✅ THIS IS A VALID PDF!")
                        
                        # Save it
                        with open(f'test_pdfs/FOUND_{voucher_no}.pdf', 'wb') as f:
                            f.write(decoded)
                        print(f"✅ Saved to test_pdfs/FOUND_{voucher_no}.pdf")
                    else:
                        print("⚠️ Not a PDF")
                except Exception as e:
                    print(f"❌ Could not decode: {e}")

print("\n" + "="*70)


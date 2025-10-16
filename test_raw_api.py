"""
Raw API Test - See exactly what ACS returns
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

def test_print_voucher_raw(voucher_no):
    """Test the print voucher endpoint and show raw response"""
    
    print("="*70)
    print(f"RAW API TEST: Print Voucher {voucher_no}")
    print("="*70)
    
    # Build request exactly as documentation says
    payload = {
        "ACSAlias": "ACS_Print_Voucher_V2",
        "ACSInputParameters": {
            "Company_ID": COMPANY_ID,
            "Company_Password": COMPANY_PASSWORD,
            "User_ID": USER_ID,
            "User_Password": USER_PASSWORD,
            "Voucher_No": voucher_no,
            "Print_Type": 2,  # Laser
            "Start_Position": 1,
            "Language": "GR"
        }
    }
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
        'AcsApiKey': API_KEY
    }
    
    print("\n--- REQUEST ---")
    print(f"URL: {BASE_URL}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            BASE_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print("\n--- RESPONSE ---")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        print("\n--- RESPONSE BODY ---")
        try:
            response_data = response.json()
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
            
            # Analyze the response
            print("\n--- ANALYSIS ---")
            has_error = response_data.get('ACSExecution_HasError')
            error_msg = response_data.get('ACSExecutionErrorMessage')
            
            print(f"Has Error: {has_error}")
            print(f"Error Message: {error_msg}")
            
            output_response = response_data.get('ACSOutputResponce', {})
            print(f"\nACSOutputResponce keys: {list(output_response.keys())}")
            
            value_output = output_response.get('ACSValueOutput', [])
            table_output = output_response.get('ACSTableOutput', {})
            object_output = output_response.get('ACSObjectOutput', [])
            
            print(f"ACSValueOutput: {value_output}")
            print(f"ACSTableOutput: {table_output}")
            print(f"ACSObjectOutput length: {len(object_output) if object_output else 0}")
            
            if object_output:
                print(f"ACSObjectOutput type: {type(object_output)}")
                print(f"ACSObjectOutput content (first 200 chars): {str(object_output)[:200]}")
            
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            print(f"Raw text: {response.text[:1000]}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        voucher_no = sys.argv[1]
    else:
        voucher_no = "7401461340"  # Default
    
    test_print_voucher_raw(voucher_no)


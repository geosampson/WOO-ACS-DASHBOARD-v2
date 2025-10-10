"""
ACS API Test Script
Quick test to check API connectivity and permissions
"""

import requests
import json
from requests.auth import HTTPBasicAuth

# Your ACS credentials
API_KEY = "5a959ce1aad74eea90a95cbc700bf32b"
COMPANY_ID = "999630747_acs"
COMPANY_PASSWORD = "SBBEm7T9"
USER_ID = "apiRouS"
USER_PASSWORD = "NJgXeHkL"
BILLING_CODE = "2ΠΓ550690"

BASE_URL = "https://webservices.acscourier.net/ACSRestServices/api/ACSAutoRest"

def build_auth():
    """Build authentication object"""
    return {
        "ACSApiKey": API_KEY,
        "Company_Id": COMPANY_ID,
        "Company_Password": COMPANY_PASSWORD,
        "User_Id": USER_ID,
        "User_Password": USER_PASSWORD
    }

def test_get_stations():
    """Test GetStations endpoint (read-only)"""
    print("\n" + "="*60)
    print("TEST 1: GetStations (Read-Only)")
    print("="*60)
    
    endpoint = f"{BASE_URL}/GetStations"
    
    request_data = {
        "ACSTable1": [{
            **build_auth()
        }]
    }
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json'
    }
    
    try:
        print(f"URL: {endpoint}")
        print(f"Method: POST")
        print(f"Headers: {headers}")
        
        response = requests.post(endpoint, json=request_data, headers=headers, timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! API is accessible")
            data = response.json()
            print(f"Received {len(data)} stations")
            if data:
                print(f"First station: {data[0]}")
        elif response.status_code == 405:
            print("\n❌ 405 Method Not Allowed")
            print("   Possible reasons:")
            print("   1. Test credentials don't have permissions")
            print("   2. Endpoint requires different HTTP method")
            print("   3. API configuration issue")
        else:
            print(f"\n⚠️ Unexpected status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

def test_create_voucher():
    """Test CreatVoucher endpoint (write operation)"""
    print("\n" + "="*60)
    print("TEST 2: CreatVoucher (Write Operation)")
    print("="*60)
    
    endpoint = f"{BASE_URL}/CreatVoucher"
    
    # Minimal test voucher
    voucher = {
        "ACSTable1": [{
            **build_auth(),
            "Billing_Code": BILLING_CODE,
            
            # Sender
            "Sender_Name": "ROUSSAKIS SUPPLIES IKE",
            "Sender_Address": "Γ. ΠΑΠΑΝΔΡΕΟΥ & ΦΑΝΑΡΙΣΤΑ",
            "Sender_City": "ΑΣΠΡΟΠΥΡΓΟΣ",
            "Sender_Zipcode": "19300",
            "Sender_Phone": "2105571070",
            
            # Recipient (test data)
            "Recipient_Name": "TEST ORDER",
            "Recipient_Address": "ΔΟΚΙΜΗ 123",
            "Recipient_City": "ΑΘΗΝΑ",
            "Recipient_Zipcode": "10100",
            "Recipient_Phone": "2101234567",
            
            # Shipment
            "Weight": 1.0,
            "Pieces": 1,
            "Cod_Amount": 0,
            "Service_Type": "1",
            "Item_Description": "TEST",
            "Fragile": "0",
            "Insurance": "0"
        }]
    }
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json'
    }
    
    try:
        print(f"URL: {endpoint}")
        print(f"Method: POST")
        print(f"Payload size: {len(json.dumps(voucher))} bytes")
        
        response = requests.post(endpoint, json=voucher, headers=headers, timeout=30)
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! Voucher created")
            result = response.json()
            print(f"Result: {result}")
            if result and len(result) > 0:
                voucher_no = result[0].get('Voucher_No')
                if voucher_no:
                    print(f"Voucher Number: {voucher_no}")
                else:
                    error = result[0].get('Error_Description', 'Unknown error')
                    print(f"Error: {error}")
        elif response.status_code == 405:
            print("\n❌ 405 Method Not Allowed")
            print("   Your test credentials likely don't have permission to create vouchers")
            print("   Contact ACS support to:")
            print("   1. Activate voucher creation for test account")
            print("   2. Get production credentials")
        else:
            print(f"\n⚠️ Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

def main():
    print("="*60)
    print("ACS API TEST SCRIPT")
    print("="*60)
    print(f"Company ID: {COMPANY_ID}")
    print(f"API Key: {API_KEY[:20]}...")
    
    # Test 1: Read-only endpoint
    test_get_stations()
    
    # Test 2: Write endpoint
    test_create_voucher()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("If both tests show 405 errors:")
    print("  → Contact ACS to activate your test credentials")
    print("\nIf GetStations works but CreatVoucher doesn't:")
    print("  → Your credentials need 'write' permissions")
    print("  → Ask ACS to enable voucher creation")
    print("\nIf both work:")
    print("  → Integration should work! Check the main app")
    print("="*60)

if __name__ == "__main__":
    main()
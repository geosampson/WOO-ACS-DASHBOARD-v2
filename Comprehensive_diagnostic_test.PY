"""
ACS API COMPREHENSIVE DIAGNOSTIC TEST
Tests everything to find the EXACT problem
"""

import requests
import json
from datetime import date

print("="*70)
print("ACS API COMPREHENSIVE DIAGNOSTIC TEST")
print("="*70)
print()

# Your credentials
CREDENTIALS = {
    "Company_ID": "999630747_acs",
    "Company_Password": "SBBEm7T9",
    "User_ID": "apiRouS",
    "User_Password": "NJgXeHkL"
}

API_KEY = "5a959ce1aad74eea90a95cbc700bf32b"
BASE_URL = "https://webservices.acscourier.net/ACSRestServices/api/ACSAutoRest"

# Different billing code variations to test
BILLING_CODES = {
    "original": "2ΠΓ550690",      # With Greek letters
    "no_greek": "2550690",         # No Greek letters
    "latin": "2PG550690",          # Greek → Latin (Π→P, Γ→G)
    "with_dash": "2-550690",       # With dash
}

print("📋 YOUR CREDENTIALS:")
print("-" * 70)
for key, value in CREDENTIALS.items():
    print(f"  {key}: {value}")
print(f"  API Key: {API_KEY[:20]}...")
print(f"  Base URL: {BASE_URL}")
print()

# Headers for all requests
headers = {
    "AcsApiKey": API_KEY,
    "Content-Type": "application/json"
}

# Test 1: Basic connectivity
print("="*70)
print("TEST 1: API ENDPOINT CONNECTIVITY")
print("="*70)
try:
    response = requests.get("https://webservices.acscourier.net", timeout=5)
    print("✅ ACS server is reachable")
    print(f"   HTTP Status: {response.status_code}")
except Exception as e:
    print(f"❌ Cannot reach ACS server: {e}")
    print("   Check your internet connection!")
print()

# Test 2: API Key validity
print("="*70)
print("TEST 2: API KEY VALIDATION")
print("="*70)

test_payload = {
    "ACSAlias": "ACS_Login",
    "ACSInputParameters": CREDENTIALS
}

try:
    response = requests.post(BASE_URL, json=test_payload, headers=headers, timeout=10)
    
    print(f"HTTP Status Code: {response.status_code}")
    
    if response.status_code == 403:
        print("❌ API KEY IS INVALID!")
        print("   The API key is rejected by ACS")
        print("   Contact ACS to get correct API key")
    elif response.status_code == 200:
        print("✅ API Key accepted")
        result = response.json()
        
        print("\nFull API Response:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get('ACSExecution_HasError') == False:
            print("\n✅ AUTHENTICATION SUCCESSFUL!")
            print("   Your credentials are VALID")
        else:
            error_msg = result.get('ACSExecutionErrorMessage', 'Unknown error')
            print(f"\n❌ AUTHENTICATION FAILED")
            print(f"   Error: {error_msg}")
            
            if "credential" in error_msg.lower() or "password" in error_msg.lower():
                print("\n   → Problem: Wrong username/password")
                print("   → Action: Check your Company_Password and User_Password")
            elif "company" in error_msg.lower():
                print("\n   → Problem: Company ID not recognized")
                print("   → Action: Verify Company_ID with ACS")
    else:
        print(f"⚠️  Unexpected HTTP status: {response.status_code}")
        print(f"   Response: {response.text[:500]}")

except Exception as e:
    print(f"❌ Request failed: {e}")
print()

# Test 3: Try creating voucher with each billing code variation
print("="*70)
print("TEST 3: BILLING CODE VALIDATION (Testing All Variations)")
print("="*70)

for name, billing_code in BILLING_CODES.items():
    print(f"\n--- Testing: {name} → '{billing_code}' ---")
    
    test_voucher = {
        "ACSAlias": "ACS_Create_Voucher",
        "ACSInputParameters": {
            **CREDENTIALS,
            "Pickup_Date": date.today().strftime('%Y-%m-%d'),
            "Sender": "ROUSSAKIS SUPPLIES IKE",
            
            "Recipient_Name": "Test Customer",
            "Recipient_Address": "Test Street",
            "Recipient_Address_Number": "1",
            "Recipient_Zipcode": "19300",
            "Recipient_Region": "ΑΣΠΡΟΠΥΡΓΟΣ",
            "Recipient_Country": "GR",
            "Recipient_Phone": "2105551234",
            "Recipient_Cell_Phone": "2105551234",
            
            "Billing_Code": billing_code,  # Testing this variation
            "Charge_Type": 2,
            "Item_Quantity": 1,
            "Item_Weight": 0.5,
            "Service_Type": 2
        }
    }
    
    try:
        response = requests.post(BASE_URL, json=test_voucher, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('ACSExecution_HasError') == False:
                print(f"   ✅ SUCCESS! This billing code WORKS!")
                voucher_no = result.get('ACSOutputResponce', {}).get('Voucher_No')
                print(f"   ✅ Test voucher created: {voucher_no}")
                print(f"\n   🎉 FOUND THE CORRECT BILLING CODE: {billing_code}")
                print(f"\n   ⚠️  UPDATE YOUR acs_api.py LINE 47 TO USE: {billing_code}")
                break
            else:
                error_msg = result.get('ACSExecutionErrorMessage', 'Unknown')
                print(f"   ❌ Failed: {error_msg}")
                
                # Analyze the error
                if "κωδικός χρέωσης" in error_msg or "billing" in error_msg.lower():
                    print(f"   → This billing code is INVALID")
                elif "συγχρονισμού" in error_msg or "synchron" in error_msg.lower():
                    print(f"   → Account not synchronized yet (ACS issue)")
                elif "ενεργοποι" in error_msg or "activ" in error_msg.lower():
                    print(f"   → Account not activated (ACS issue)")
                else:
                    print(f"   → Other issue: {error_msg}")
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text[:200]}")
    
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

print()

# Test 4: Check if it's a timing/account status issue
print("="*70)
print("TEST 4: ACCOUNT STATUS CHECK")
print("="*70)

# Try a simple query that shouldn't require billing code
try:
    # Try to get tracking info (should work even without billing code)
    tracking_test = {
        "ACSAlias": "ACS_Get_Voucher_Status",
        "ACSInputParameters": {
            **CREDENTIALS,
            "Voucher_No": "8000000000"  # Fake voucher
        }
    }
    
    response = requests.post(BASE_URL, json=tracking_test, headers=headers, timeout=10)
    
    if response.status_code == 200:
        result = response.json()
        
        if result.get('ACSExecution_HasError') == False:
            print("✅ Account can make API calls successfully")
            print("   → Problem is ONLY with billing code or voucher creation")
        else:
            error_msg = result.get('ACSExecutionErrorMessage', 'Unknown')
            print(f"⚠️  API call failed: {error_msg}")
            
            if "account" in error_msg.lower() or "συγχρονισμ" in error_msg:
                print("   → Account not fully activated (ACS issue)")
            elif "voucher" in error_msg.lower():
                print("   → This is OK - we used a fake voucher number")
                print("   ✅ Your account CAN make API calls")

except Exception as e:
    print(f"⚠️  Test failed: {e}")

print()

# Final diagnosis
print("="*70)
print("DIAGNOSTIC SUMMARY")
print("="*70)
print()

# Check what we learned
print("📊 TEST RESULTS:")
print()

# You'll need to interpret based on the results above
print("Based on the tests above, here's what the problem is:")
print()
print("IF you see '✅ SUCCESS' for any billing code:")
print("  → Problem: Wrong billing code in your code")
print("  → Solution: Update acs_api.py with the working code")
print()
print("IF all billing codes failed with 'κωδικός χρέωσης' error:")
print("  → Problem: ACS account not activated")
print("  → Solution: Call ACS - account needs activation")
print()
print("IF you see 'API KEY IS INVALID':")
print("  → Problem: Wrong API key")
print("  → Solution: Get correct API key from ACS")
print()
print("IF authentication failed:")
print("  → Problem: Wrong credentials")
print("  → Solution: Check Company_Password and User_Password")
print()

print("="*70)
print("NEXT STEPS")
print("="*70)
print()

print("1. Look at the test results above")
print("2. Find which test FAILED")
print("3. Follow the solution for that specific test")
print()
print("4. If ALL billing codes failed with 'ανυπάρκτος κωδικός χρέωσης':")
print("   → This means ACS account is NOT activated")
print("   → Call ACS NOW: 801 300 0000")
print("   → Tell them: 'Account 999630747_acs still not activated after 1 week'")
print()
print("5. If ONE billing code WORKED:")
print("   → Update your acs_api.py line 47 with that billing code")
print("   → Run your app again")
print("   → Should work!")
print()

print("="*70)
print()
print("💡 TIP: Take a screenshot of this output and send it to ACS support!")
print("         It will help them diagnose the issue quickly.")
print()
print("="*70)
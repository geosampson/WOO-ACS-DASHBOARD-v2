"""
Test PDF Printing Issue - Diagnostic Script
This will help identify why PDFs are not being generated/saved
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from acs_api import ACSCourierAPI
import json
from datetime import date

def test_print_voucher_with_existing_voucher():
    """
    Test printing a voucher that already exists
    You need to provide a valid voucher number that you've already created
    """
    print("="*70)
    print("ACS PDF PRINTING DIAGNOSTIC TEST")
    print("="*70)
    
    # Initialize API
    api = ACSCourierAPI()
    
    # Ask for voucher number
    print("\nThis test will try to download a PDF for an existing voucher.")
    print("Please enter a voucher number that you've already created via the API:")
    print("(If you don't have one, type 'create' to create a test voucher first)")
    
    voucher_no = input("\nVoucher Number: ").strip()
    
    if voucher_no.lower() == 'create':
        print("\n" + "="*70)
        print("CREATING TEST VOUCHER")
        print("="*70)
        
        # Create a test voucher
        test_shipment = {
            'recipient_name': 'TEST PDF DOWNLOAD',
            'recipient_address': 'ΔΟΚΙΜΗΣ',
            'recipient_address_number': '1',
            'recipient_zipcode': '10100',
            'recipient_region': 'ΑΘΗΝΑ',
            'recipient_phone': '2101234567',
            'weight': 0.5,
            'pieces': 1,
            'delivery_notes': 'Test for PDF printing'
        }
        
        print("\nCreating voucher...")
        result = api.create_voucher(test_shipment)
        
        if result['success']:
            voucher_no = result['voucher_no']
            print(f"✅ Voucher created successfully: {voucher_no}")
        else:
            print(f"❌ Failed to create voucher: {result.get('error')}")
            return
    
    if not voucher_no:
        print("❌ No voucher number provided. Exiting.")
        return
    
    # Test PDF printing
    print("\n" + "="*70)
    print(f"TESTING PDF DOWNLOAD FOR VOUCHER: {voucher_no}")
    print("="*70)
    
    # Create output directory
    output_dir = "test_pdfs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test 1: Laser format (Print_Type=2)
    print("\n--- Test 1: Laser Format (Print_Type=2) ---")
    pdf_path_laser = os.path.join(output_dir, f"voucher_{voucher_no}_laser.pdf")
    
    print(f"Attempting to download PDF to: {pdf_path_laser}")
    print("This may take a few seconds with retries...")
    
    result = api.print_voucher(
        voucher_no=voucher_no,
        print_type=2,  # Laser A4
        output_path=pdf_path_laser,
        retry_delay=3,
        max_retries=3
    )
    
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    if result['success']:
        print(f"\n✅ SUCCESS! PDF saved to: {pdf_path_laser}")
        print(f"   File size: {os.path.getsize(pdf_path_laser)} bytes")
        
        # Try to open it
        try:
            if sys.platform == 'win32':
                os.startfile(pdf_path_laser)
            elif sys.platform == 'darwin':
                os.system(f'open "{pdf_path_laser}"')
            else:
                os.system(f'xdg-open "{pdf_path_laser}"')
            print("   Opened PDF in default viewer")
        except:
            print("   (Could not auto-open PDF)")
    else:
        print(f"\n❌ FAILED: {result.get('error')}")
        print("\nPossible reasons:")
        print("1. PDF not ready yet - ACS may need time to generate it")
        print("2. Voucher number doesn't exist")
        print("3. API permissions issue")
        print("4. Network/connection problem")
    
    # Test 2: Thermal format (Print_Type=1)
    print("\n\n--- Test 2: Thermal Format (Print_Type=1) ---")
    pdf_path_thermal = os.path.join(output_dir, f"voucher_{voucher_no}_thermal.pdf")
    
    print(f"Attempting to download PDF to: {pdf_path_thermal}")
    
    result = api.print_voucher(
        voucher_no=voucher_no,
        print_type=1,  # Thermal
        output_path=pdf_path_thermal,
        retry_delay=3,
        max_retries=3
    )
    
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    if result['success']:
        print(f"\n✅ SUCCESS! PDF saved to: {pdf_path_thermal}")
        print(f"   File size: {os.path.getsize(pdf_path_thermal)} bytes")
    else:
        print(f"\n❌ FAILED: {result.get('error')}")
    
    # Test 3: Get base64 without saving
    print("\n\n--- Test 3: Get PDF as Base64 (no file save) ---")
    
    result = api.print_voucher(
        voucher_no=voucher_no,
        print_type=2,
        output_path=None  # Don't save, just get base64
    )
    
    if result['success']:
        pdf_base64 = result.get('pdf_base64', '')
        print(f"\n✅ SUCCESS! Got base64 PDF data")
        print(f"   Base64 length: {len(pdf_base64)} characters")
        print(f"   First 100 chars: {pdf_base64[:100]}...")
        
        # Try to decode and save manually
        import base64
        try:
            pdf_bytes = base64.b64decode(pdf_base64)
            manual_path = os.path.join(output_dir, f"voucher_{voucher_no}_manual.pdf")
            with open(manual_path, 'wb') as f:
                f.write(pdf_bytes)
            print(f"\n✅ Manually saved PDF to: {manual_path}")
            print(f"   File size: {len(pdf_bytes)} bytes")
            
            # Check if it's a valid PDF
            if pdf_bytes.startswith(b'%PDF'):
                print("   ✅ Valid PDF header detected")
            else:
                print("   ⚠️ WARNING: Doesn't look like a valid PDF")
                print(f"   First 20 bytes: {pdf_bytes[:20]}")
        except Exception as e:
            print(f"\n❌ Failed to decode/save: {e}")
    else:
        print(f"\n❌ FAILED: {result.get('error')}")
    
    # Summary
    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)
    print(f"Voucher Number: {voucher_no}")
    print(f"Output Directory: {output_dir}/")
    print("\nFiles created:")
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)
        print(f"  - {filename} ({os.path.getsize(filepath)} bytes)")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    test_print_voucher_with_existing_voucher()


# Quick Start Guide - ACS Voucher System

## 🚀 Your System is Now Fixed and Ready!

---

## What Was Fixed

✅ **PDF Download Bug** - Vouchers now download correctly  
✅ **3-Sticker Format** - New tool for laser printer labels  
✅ **Complete Testing** - All features verified working

---

## How to Use

### 1. Create and Download a Voucher

#### Option A: Using the Dashboard GUI
```bash
python3 1759856941497_woocommerce_only_dashboard.py
```

1. Click "Create ACS Voucher"
2. Fill in recipient details (or select from WooCommerce orders)
3. Click "Submit"
4. PDF will be automatically downloaded

#### Option B: Using the API Directly
```python
from acs_api import ACSCourierAPI

api = ACSCourierAPI()

# Create voucher
shipment = {
    'recipient_name': 'CUSTOMER NAME',
    'recipient_address': 'STREET NAME',
    'recipient_address_number': '123',
    'recipient_zipcode': '12345',
    'recipient_region': 'CITY',
    'recipient_phone': '2101234567',
    'weight': 1.0,
    'pieces': 1,
    'delivery_notes': 'Handle with care'
}

result = api.create_voucher(shipment)

if result['success']:
    voucher_no = result['voucher_no']
    print(f"Voucher created: {voucher_no}")
    
    # Download PDF
    pdf_result = api.print_voucher(
        voucher_no=voucher_no,
        print_type=2,  # 2=Laser, 1=Thermal
        output_path=f'voucher_{voucher_no}.pdf'
    )
    
    if pdf_result['success']:
        print(f"PDF saved: {pdf_result['file_path']}")
```

---

### 2. Convert to 3-Sticker Format

After downloading a voucher PDF, convert it to 3-sticker A4 format:

```bash
python3 pdf_to_3stickers.py voucher_7401461340.pdf
```

**Output:** `voucher_7401461340_3stickers.pdf`

This creates a single A4 page with 3 identical copies of the voucher, perfect for:
- Pre-cut sticker paper (3 labels per A4 sheet)
- Laser printers
- One for parcel, one for invoice, one for your records

---

### 3. Print the Voucher

#### Windows:
```python
import os
os.startfile('voucher_7401461340_3stickers.pdf')
```

#### Linux:
```bash
lpr voucher_7401461340_3stickers.pdf
```

#### Mac:
```bash
lp voucher_7401461340_3stickers.pdf
```

---

## 📋 Complete Workflow Example

```python
from acs_api import ACSCourierAPI
from pdf_to_3stickers import create_3stickers_with_images
import os

# 1. Initialize API
api = ACSCourierAPI()

# 2. Create voucher
shipment = {
    'recipient_name': 'JOHN DOE',
    'recipient_address': 'ATHINAS',
    'recipient_address_number': '25',
    'recipient_zipcode': '10100',
    'recipient_region': 'ATHENS',
    'recipient_phone': '2101234567',
    'weight': 0.5,
    'pieces': 1
}

result = api.create_voucher(shipment)

if result['success']:
    voucher_no = result['voucher_no']
    
    # 3. Download laser PDF
    pdf_path = f'vouchers/voucher_{voucher_no}_laser.pdf'
    api.print_voucher(voucher_no, print_type=2, output_path=pdf_path)
    
    # 4. Convert to 3-sticker format
    sticker_pdf = create_3stickers_with_images(pdf_path)
    
    # 5. Print (Windows)
    os.startfile(sticker_pdf)
    
    print(f"✅ Voucher {voucher_no} ready!")
    print(f"   3-Sticker PDF: {sticker_pdf}")
```

---

## 🧪 Testing

### Test PDF Download
```bash
python3 test_pdf_printing.py
```

Enter an existing voucher number (e.g., `7401461340`) to test downloading.

### Test 3-Sticker Conversion
```bash
python3 pdf_to_3stickers.py test_pdfs/voucher_7401461340_laser.pdf
```

### Test Raw API
```bash
python3 test_raw_api.py 7401461340
```

---

## 📁 File Locations

**Downloaded PDFs:**
- Single voucher: `voucher_XXXXXXXXXX_laser.pdf`
- 3-sticker format: `voucher_XXXXXXXXXX_laser_3stickers.pdf`

**Database:**
- Shipment tracking: `acs_shipments.db`

**Logs:**
- API calls and errors are logged to console

---

## 🎨 Print Settings Recommendations

### For 3-Sticker A4 Labels

**Printer Settings:**
- Paper size: A4 (210 x 297 mm)
- Orientation: Portrait
- Quality: High / Best
- Color: Black & White (to save ink)
- Scale: 100% (no scaling)

**Sticker Paper:**
- Type: Pre-cut A4 sticker sheets
- Layout: 3 labels per sheet (horizontal divisions)
- Each label: ~210mm x 99mm

**Cutting:**
- Use the dashed lines as guides
- Cut horizontally between stickers
- Each sticker is identical (use any of the 3)

---

## ❓ Troubleshooting

### Problem: PDF Download Fails

**Solution:**
```bash
python3 test_pdf_printing.py
```

Enter your voucher number and check the detailed error messages.

### Problem: "PDFData field not found"

**Cause:** Voucher might not exist or API credentials issue

**Solution:**
1. Verify voucher number is correct
2. Check if voucher was created successfully
3. Try creating a new test voucher

### Problem: 3-Sticker Conversion Fails

**Solution:**
```bash
# Install dependencies
pip3 install pdf2image pillow PyPDF2

# On Linux, also install poppler
sudo apt-get install poppler-utils
```

### Problem: Barcode Not Scanning

**Cause:** Print quality too low

**Solution:**
- Increase printer quality to "High" or "Best"
- Ensure paper is loaded correctly
- Clean printer heads
- Use original ACS PDF if 3-sticker version has issues

---

## 📞 Need Help?

1. **Check the logs** - Error messages are detailed
2. **Run test scripts** - They provide diagnostic info
3. **Check FIXES_APPLIED.md** - Technical details
4. **Review ACS documentation** - `acs-web-services-07-25(1).pdf`

---

## 🎯 Tips for Efficiency

### Batch Processing
Create multiple vouchers at once:

```python
api = ACSCourierAPI()

vouchers = []
for order in woocommerce_orders:
    result = api.create_voucher(order)
    if result['success']:
        vouchers.append(result['voucher_no'])

# Download all
for voucher_no in vouchers:
    api.print_voucher(voucher_no, print_type=2, output_path=f'voucher_{voucher_no}.pdf')
```

### Auto-Print
Set up automatic printing after voucher creation:

```python
def create_and_print(shipment):
    result = api.create_voucher(shipment)
    if result['success']:
        voucher_no = result['voucher_no']
        pdf_path = f'voucher_{voucher_no}.pdf'
        api.print_voucher(voucher_no, print_type=2, output_path=pdf_path)
        
        # Convert to 3-sticker
        sticker_pdf = create_3stickers_with_images(pdf_path)
        
        # Auto-print
        os.startfile(sticker_pdf)  # Windows
        
        return voucher_no
```

### Database Tracking
All vouchers are automatically saved to `acs_shipments.db`:

```python
import sqlite3

conn = sqlite3.connect('acs_shipments.db')
cursor = conn.cursor()

# Get all shipments
cursor.execute("SELECT * FROM shipments ORDER BY created_at DESC LIMIT 10")
recent_shipments = cursor.fetchall()

for shipment in recent_shipments:
    print(f"Voucher: {shipment[1]}, Status: {shipment[3]}")
```

---

## ✅ You're All Set!

Your ACS voucher system is now:
- ✅ Fully functional
- ✅ Tested and verified
- ✅ Ready for production use
- ✅ Documented

**Happy shipping!** 🚚📦

---

**Last Updated:** October 16, 2025  
**Version:** 2.0 (Post-Fix)


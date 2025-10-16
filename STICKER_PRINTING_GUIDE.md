# Sticker Printing Guide

## 📋 Overview

You now have **TWO** tools for printing ACS vouchers on sticker paper:

1. **`pdf_to_3stickers.py`** - Print 3 identical copies (for fresh sheets)
2. **`pdf_to_single_sticker.py`** - Print on specific position (for partially used sheets)

---

## 🎯 When to Use Each Tool

### Use `pdf_to_3stickers.py` when:
- ✅ You have a **fresh, unused** A4 sticker sheet
- ✅ You want **3 identical copies** of the same voucher
- ✅ You need multiple copies (one for parcel, one for invoice, one for records)

### Use `pdf_to_single_sticker.py` when:
- ✅ You have a **partially used** sticker sheet
- ✅ Some positions are already used/missing
- ✅ You need to print on a **specific position** (top, middle, or bottom)

---

## 📦 Tool 1: 3-Sticker Format (Full Sheet)

### Usage:
```bash
python3 pdf_to_3stickers.py voucher_7401462180.pdf
```

### Output:
- **File:** `voucher_7401462180_3stickers.pdf`
- **Layout:** 3 identical vouchers on one A4 page
- **Positions:** Top, Middle, Bottom (all filled)

### Example:
```
┌─────────────────────┐
│  VOUCHER #7401...   │  ← Position 1 (Top)
├─────────────────────┤
│  VOUCHER #7401...   │  ← Position 2 (Middle)
├─────────────────────┤
│  VOUCHER #7401...   │  ← Position 3 (Bottom)
└─────────────────────┘
```

---

## 🎯 Tool 2: Single Sticker at Specific Position

### Usage:

#### Print on Top Position:
```bash
python3 pdf_to_single_sticker.py voucher_7401462180.pdf 1
```

#### Print on Middle Position:
```bash
python3 pdf_to_single_sticker.py voucher_7401462180.pdf 2
```

#### Print on Bottom Position:
```bash
python3 pdf_to_single_sticker.py voucher_7401462180.pdf 3
```

#### Create All 3 Positions (separate files):
```bash
python3 pdf_to_single_sticker.py voucher_7401462180.pdf all
```

### Output Files:
- **Top:** `voucher_7401462180_sticker_top.pdf`
- **Middle:** `voucher_7401462180_sticker_middle.pdf`
- **Bottom:** `voucher_7401462180_sticker_bottom.pdf`

### Example (Middle Position):
```
┌─────────────────────┐
│                     │  ← Position 1 (Empty)
├─────────────────────┤
│  VOUCHER #7401...   │  ← Position 2 (Printed) ✅
├─────────────────────┤
│                     │  ← Position 3 (Empty)
└─────────────────────┘
```

---

## 🖨️ Printing Instructions

### Step 1: Choose Your Scenario

**Scenario A: Fresh Sheet (All 3 Positions Empty)**
```bash
# Create 3-sticker PDF
python3 pdf_to_3stickers.py voucher_7401462180.pdf

# Print the output
# Windows: Right-click PDF → Print
# Linux: lpr voucher_7401462180_3stickers.pdf
```

**Scenario B: Partially Used Sheet (e.g., Top Used, Middle Empty)**
```bash
# Create single sticker for middle position
python3 pdf_to_single_sticker.py voucher_7401462180.pdf 2

# Print the output
# The voucher will print ONLY in the middle position
```

### Step 2: Printer Settings

**Important Settings:**
- **Paper Size:** A4 (210 x 297 mm)
- **Orientation:** Portrait
- **Scale:** 100% (no scaling!)
- **Quality:** High/Best
- **Color:** Black & White (recommended)

**DO NOT:**
- ❌ Scale to fit page
- ❌ Auto-rotate
- ❌ Use duplex/double-sided
- ❌ Change margins

### Step 3: Load Sticker Paper

1. **Check your sticker sheet** - Which positions are empty?
2. **Load paper** - Put sticker side facing the correct direction
3. **Align properly** - Make sure paper is straight in tray

### Step 4: Print

1. **Open the PDF** you created
2. **Print** with settings above
3. **Verify** - Check that it printed in the correct position
4. **Cut** along the dashed lines if needed

---

## 📐 Sticker Sheet Layout

Your A4 sticker sheet has **3 positions**:

```
┌─────────────────────────────┐
│                             │
│   Position 1 (TOP)          │  ← ~99mm height
│                             │
├─────────────────────────────┤ ← Cutting line
│                             │
│   Position 2 (MIDDLE)       │  ← ~99mm height
│                             │
├─────────────────────────────┤ ← Cutting line
│                             │
│   Position 3 (BOTTOM)       │  ← ~99mm height
│                             │
└─────────────────────────────┘

Total: 210mm x 297mm (A4)
Each sticker: 210mm x 99mm
```

---

## 🔧 Complete Workflow Example

### Example 1: Create 3 Vouchers for 3 Different Orders

```bash
# Download vouchers
python3 -c "
from acs_api import ACSCourierAPI
api = ACSCourierAPI()

# Create 3 vouchers
vouchers = []
for order in orders:
    result = api.create_voucher(order)
    voucher_no = result['voucher_no']
    api.print_voucher(voucher_no, print_type=2, output_path=f'voucher_{voucher_no}.pdf')
    vouchers.append(voucher_no)
"

# Create single sticker for each position
python3 pdf_to_single_sticker.py voucher_AAAA.pdf 1  # Top
python3 pdf_to_single_sticker.py voucher_BBBB.pdf 2  # Middle
python3 pdf_to_single_sticker.py voucher_CCCC.pdf 3  # Bottom

# Now you have 3 different vouchers on one sheet!
```

### Example 2: You Already Used Top Position

```bash
# You have a sheet where top position is already used
# You need to print on middle position

python3 pdf_to_single_sticker.py voucher_7401462180.pdf 2

# Load your partially used sheet
# Print
# The voucher will appear ONLY in the middle position
```

---

## 🎨 Visual Features

### 3-Sticker PDF:
- ✅ 3 identical vouchers
- ✅ Dashed cutting guides
- ✅ All positions filled

### Single-Sticker PDF:
- ✅ **"POSITION: TOP/MIDDLE/BOTTOM"** label at top
- ✅ **Blue border** around active position
- ✅ Dashed cutting guides (all 3 lines)
- ✅ Only selected position has voucher
- ✅ Other positions are blank/white

---

## ❓ Troubleshooting

### Problem: Voucher prints in wrong position

**Solution:**
1. Check you used the correct position number (1, 2, or 3)
2. Make sure printer scale is 100%
3. Check paper orientation (Portrait)

### Problem: Voucher is too small/large

**Solution:**
1. Set printer scale to **100%** (no "Fit to page")
2. Check paper size is **A4**
3. Regenerate PDF if needed

### Problem: Can't see which position will print

**Solution:**
- Look for the **blue border** in the PDF
- Look for the **"POSITION: XXX"** label at the top
- The voucher is only in one section, others are blank

### Problem: Need to print same voucher on multiple positions

**Solution:**
```bash
# Create all 3 positions
python3 pdf_to_single_sticker.py voucher_7401462180.pdf all

# You'll get 3 separate PDFs:
# - voucher_7401462180_sticker_top.pdf
# - voucher_7401462180_sticker_middle.pdf
# - voucher_7401462180_sticker_bottom.pdf

# Print the ones you need
```

---

## 💡 Pro Tips

### Tip 1: Keep Partially Used Sheets Organized
- Mark which positions are used with a pen
- Store in a folder labeled "Partial Sheets"
- Always check before printing

### Tip 2: Batch Processing
```bash
# Create all positions for multiple vouchers at once
for voucher in voucher_*.pdf; do
    python3 pdf_to_single_sticker.py "$voucher" all
done
```

### Tip 3: Test First
- Print on regular paper first
- Hold it up to your sticker sheet
- Verify alignment before printing on stickers

### Tip 4: Save Ink
- Use "Draft" or "Economy" mode for test prints
- Use "High Quality" only for final sticker prints

---

## 📊 Quick Reference

| Scenario | Command | Output |
|----------|---------|--------|
| Fresh sheet, 3 copies | `pdf_to_3stickers.py voucher.pdf` | All 3 positions filled |
| Print on top | `pdf_to_single_sticker.py voucher.pdf 1` | Only top position |
| Print on middle | `pdf_to_single_sticker.py voucher.pdf 2` | Only middle position |
| Print on bottom | `pdf_to_single_sticker.py voucher.pdf 3` | Only bottom position |
| Create all options | `pdf_to_single_sticker.py voucher.pdf all` | 3 separate PDFs |

---

## ✅ Summary

You now have **complete control** over sticker printing:

1. **Fresh sheets** → Use `pdf_to_3stickers.py`
2. **Partially used sheets** → Use `pdf_to_single_sticker.py` with position number
3. **Multiple options** → Use `all` parameter to create all 3 positions

**No more wasted stickers!** 🎉

---

**Last Updated:** October 16, 2025  
**Version:** 2.0


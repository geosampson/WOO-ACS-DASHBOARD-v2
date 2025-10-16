"""
Convert ACS voucher PDF to single sticker at specific position on A4 sheet
For when you have partially used sticker sheets and need to print on a specific position
"""

from pdf2image import convert_from_path
from PIL import Image, ImageDraw
import os

def create_single_sticker_at_position(input_pdf_path, position=1, output_pdf_path=None):
    """
    Create a single voucher sticker at a specific position on A4 sheet
    
    Args:
        input_pdf_path: Path to the original ACS voucher PDF
        position: Which sticker position (1=Top, 2=Middle, 3=Bottom)
        output_pdf_path: Path to save the output PDF (optional)
        
    Returns:
        Path to the output PDF
    """
    
    if position not in [1, 2, 3]:
        raise ValueError("Position must be 1 (Top), 2 (Middle), or 3 (Bottom)")
    
    if not output_pdf_path:
        # Auto-generate output filename
        base_name = os.path.splitext(input_pdf_path)[0]
        position_names = {1: "top", 2: "middle", 3: "bottom"}
        output_pdf_path = f"{base_name}_sticker_{position_names[position]}.pdf"
    
    # Convert PDF to image
    print(f"Converting PDF to image...")
    images = convert_from_path(input_pdf_path, dpi=300)
    
    if not images:
        raise ValueError("Could not convert PDF to image")
    
    voucher_image = images[0]
    
    # A4 dimensions at 300 DPI
    a4_width_px = int(8.27 * 300)  # 2481 pixels
    a4_height_px = int(11.69 * 300)  # 3507 pixels
    
    # Create blank A4 image
    output_image = Image.new('RGB', (a4_width_px, a4_height_px), 'white')
    
    # Calculate sticker dimensions
    sticker_height_px = a4_height_px // 3
    
    # Resize voucher to fit in one sticker slot
    voucher_width, voucher_height = voucher_image.size
    
    # Calculate scale to fit
    scale_x = a4_width_px / voucher_width
    scale_y = sticker_height_px / voucher_height
    scale = min(scale_x, scale_y) * 0.90  # 90% to leave margin
    
    new_width = int(voucher_width * scale)
    new_height = int(voucher_height * scale)
    
    resized_voucher = voucher_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    print(f"Voucher resized to: {new_width} x {new_height} pixels")
    
    # Calculate Y offset based on position
    # Position 1 (Top) = 0
    # Position 2 (Middle) = sticker_height_px
    # Position 3 (Bottom) = sticker_height_px * 2
    y_offset = (position - 1) * sticker_height_px
    
    # Center horizontally
    x_center = (a4_width_px - new_width) // 2
    y_center = y_offset + (sticker_height_px - new_height) // 2
    
    # Paste the voucher at the specified position
    output_image.paste(resized_voucher, (x_center, y_center))
    
    # Draw cutting guides for all 3 positions (light gray dashed lines)
    draw = ImageDraw.Draw(output_image)
    
    for i in range(1, 3):  # Draw lines between positions
        y_line = i * sticker_height_px
        for x in range(0, a4_width_px, 20):
            draw.line([(x, y_line), (x + 10, y_line)], fill=(200, 200, 200), width=2)
    
    # Draw a border around the active sticker position (to show where it will print)
    border_color = (100, 100, 255)  # Blue
    border_width = 3
    
    # Top border
    draw.rectangle([
        10, y_offset + 10,
        a4_width_px - 10, y_offset + sticker_height_px - 10
    ], outline=border_color, width=border_width)
    
    # Add position label
    from PIL import ImageFont
    try:
        # Try to use a nice font
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        # Fallback to default
        font = ImageFont.load_default()
    
    position_names = {1: "TOP", 2: "MIDDLE", 3: "BOTTOM"}
    label_text = f"POSITION: {position_names[position]}"
    
    # Draw label at the top
    draw.text((50, 30), label_text, fill=border_color, font=font)
    
    # Save as PDF
    print(f"Saving to {output_pdf_path}...")
    output_image.save(output_pdf_path, "PDF", resolution=300.0, quality=95)
    
    print(f"✅ Single sticker PDF created at position {position} ({position_names[position]})")
    print(f"   Output: {output_pdf_path}")
    print(f"   File size: {os.path.getsize(output_pdf_path)} bytes")
    
    return output_pdf_path


def create_all_positions(input_pdf_path):
    """
    Create 3 separate PDFs, one for each sticker position
    Useful when you want to have all options ready
    
    Returns:
        List of paths to the 3 output PDFs
    """
    base_name = os.path.splitext(input_pdf_path)[0]
    
    outputs = []
    for position in [1, 2, 3]:
        output_path = create_single_sticker_at_position(input_pdf_path, position)
        outputs.append(output_path)
    
    return outputs


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 pdf_to_single_sticker.py <input_pdf> [position]")
        print("  python3 pdf_to_single_sticker.py <input_pdf> all")
        print("\nPosition:")
        print("  1 = Top sticker")
        print("  2 = Middle sticker")
        print("  3 = Bottom sticker")
        print("  all = Create all 3 positions")
        print("\nExamples:")
        print("  python3 pdf_to_single_sticker.py voucher_7401461340.pdf 2")
        print("  python3 pdf_to_single_sticker.py voucher_7401461340.pdf all")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    
    if not os.path.exists(input_pdf):
        print(f"❌ Error: File not found: {input_pdf}")
        sys.exit(1)
    
    try:
        if len(sys.argv) > 2 and sys.argv[2].lower() == 'all':
            # Create all 3 positions
            print("Creating PDFs for all 3 positions...")
            outputs = create_all_positions(input_pdf)
            print(f"\n✅ Success! Created {len(outputs)} PDFs:")
            for i, path in enumerate(outputs, 1):
                print(f"   Position {i}: {path}")
        else:
            # Create single position
            position = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            
            if position not in [1, 2, 3]:
                print("❌ Error: Position must be 1, 2, or 3")
                sys.exit(1)
            
            result = create_single_sticker_at_position(input_pdf, position)
            print(f"\n✅ Success! Single sticker PDF ready:")
            print(f"   {result}")
            print(f"\nThis will print on the {['TOP', 'MIDDLE', 'BOTTOM'][position-1]} position of your A4 sticker sheet")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


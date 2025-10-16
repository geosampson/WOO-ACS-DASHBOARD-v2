"""
Convert ACS voucher PDF to 3-sticker A4 label format
This creates 3 copies of the voucher on a single A4 page for pre-cut sticker paper
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PyPDF2 import PdfReader, PdfWriter
import io
import os

def convert_to_3stickers(input_pdf_path, output_pdf_path=None):
    """
    Convert a single ACS voucher PDF to 3-sticker A4 format
    
    Args:
        input_pdf_path: Path to the original ACS voucher PDF
        output_pdf_path: Path to save the 3-sticker version (optional)
        
    Returns:
        Path to the output PDF
    """
    
    if not output_pdf_path:
        # Auto-generate output filename
        base_name = os.path.splitext(input_pdf_path)[0]
        output_pdf_path = f"{base_name}_3stickers.pdf"
    
    # Read the original PDF
    reader = PdfReader(input_pdf_path)
    original_page = reader.pages[0]
    
    # Get original page dimensions
    orig_width = float(original_page.mediabox.width)
    orig_height = float(original_page.mediabox.height)
    
    print(f"Original PDF size: {orig_width:.1f} x {orig_height:.1f} points")
    
    # A4 dimensions in points (1 point = 1/72 inch)
    a4_width, a4_height = A4  # 595.27 x 841.89 points
    
    # Calculate sticker dimensions
    # 3 stickers vertically on A4
    sticker_height = a4_height / 3  # ~280.6 points per sticker
    sticker_width = a4_width  # Full width
    
    # Calculate scale to fit the voucher into one sticker slot
    scale_x = sticker_width / orig_width
    scale_y = sticker_height / orig_height
    scale = min(scale_x, scale_y) * 0.95  # 95% to leave some margin
    
    # Calculate centered position
    scaled_width = orig_width * scale
    scaled_height = orig_height * scale
    
    # Create output PDF with reportlab
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    
    # Draw 3 copies of the voucher
    for i in range(3):
        # Y position for this sticker (from bottom)
        y_offset = i * sticker_height
        
        # Center the voucher in the sticker slot
        x_center = (sticker_width - scaled_width) / 2
        y_center = y_offset + (sticker_height - scaled_height) / 2
        
        # Draw a light border around each sticker (for cutting guide)
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.setLineWidth(0.5)
        c.setDash([2, 2])
        c.rect(5, y_offset + 5, sticker_width - 10, sticker_height - 10)
        
        # Save the state
        c.saveState()
        
        # Move to position and scale
        c.translate(x_center, y_center)
        c.scale(scale, scale)
        
        # We'll overlay the original PDF on top of this
        # For now, just mark the position
        c.restoreState()
    
    c.save()
    
    # Now merge with the original PDF
    packet.seek(0)
    background = PdfReader(packet)
    background_page = background.pages[0]
    
    # Create output writer
    output = PdfWriter()
    
    # For each sticker position, we need to overlay the original voucher
    # This is complex with PyPDF2, so let's use a simpler approach with reportlab
    
    # Actually, let's use pdf2image and PIL for better control
    return create_3stickers_with_images(input_pdf_path, output_pdf_path)


def create_3stickers_with_images(input_pdf_path, output_pdf_path=None):
    """
    Create 3-sticker layout using PDF rendering
    This method converts PDF to image and back for better control
    """
    from pdf2image import convert_from_path
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    
    # Generate output path if not provided
    if not output_pdf_path:
        base_name = os.path.splitext(input_pdf_path)[0]
        output_pdf_path = f"{base_name}_3stickers.pdf"
    
    # Convert PDF to image
    print("Converting PDF to image...")
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
    
    # Paste 3 copies
    for i in range(3):
        y_offset = i * sticker_height_px
        
        # Center horizontally
        x_center = (a4_width_px - new_width) // 2
        y_center = y_offset + (sticker_height_px - new_height) // 2
        
        output_image.paste(resized_voucher, (x_center, y_center))
        
        # Draw cutting guides
        from PIL import ImageDraw
        draw = ImageDraw.Draw(output_image)
        
        # Dashed line at top of each sticker (except first)
        if i > 0:
            y_line = y_offset
            for x in range(0, a4_width_px, 20):
                draw.line([(x, y_line), (x + 10, y_line)], fill=(200, 200, 200), width=2)
    
    # Save as PDF
    print(f"Saving to {output_pdf_path}...")
    output_image.save(output_pdf_path, "PDF", resolution=300.0, quality=95)
    
    print(f"✅ 3-sticker PDF created: {output_pdf_path}")
    print(f"   File size: {os.path.getsize(output_pdf_path)} bytes")
    
    return output_pdf_path


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 pdf_to_3stickers.py <input_pdf> [output_pdf]")
        print("\nExample:")
        print("  python3 pdf_to_3stickers.py voucher_7401461340_laser.pdf")
        print("  python3 pdf_to_3stickers.py voucher.pdf voucher_3stickers.pdf")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_pdf):
        print(f"❌ Error: File not found: {input_pdf}")
        sys.exit(1)
    
    try:
        result = create_3stickers_with_images(input_pdf, output_pdf)
        print(f"\n✅ Success! 3-sticker PDF ready for printing:")
        print(f"   {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


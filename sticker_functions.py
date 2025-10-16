"""
Sticker position functions to add to acs_integration.py
Add these methods to the ACSShippingTab class
"""

def create_3sticker_pdf(self):
    """Create 3-sticker format PDF for selected voucher"""
    from pdf_to_3stickers import create_3stickers_with_images
    
    selection = self.shipments_tree.selection()
    
    if not selection:
        messagebox.showwarning("No Selection", "Please select a shipment first")
        return
    
    item = selection[0]
    values = self.shipments_tree.item(item, 'values')
    shipment_id = values[0]
    voucher_no = values[1]
    
    if not voucher_no or voucher_no == '-':
        messagebox.showerror("No Voucher", "This shipment doesn't have a voucher yet")
        return
    
    # Check if original PDF exists
    shipment = self.acs_db.get_shipment(shipment_id=shipment_id)
    original_pdf = None
    
    if shipment and shipment.get('pdf_path'):
        original_pdf = Path(shipment['pdf_path'])
        if not original_pdf.exists():
            original_pdf = None
    
    # If no PDF, download it first
    if not original_pdf:
        self.log(f"📄 Downloading voucher {voucher_no} first...")
        
        temp_pdf = self.pdf_today_folder / f"voucher_{voucher_no}_temp.pdf"
        
        result = self.acs_api.print_voucher(
            voucher_no=voucher_no,
            print_type=2,
            output_path=str(temp_pdf)
        )
        
        if not result['success']:
            error_msg = result.get('error', 'Unknown error')
            messagebox.showerror("Download Failed", f"Failed to download PDF:\n\n{error_msg}")
            return
        
        original_pdf = temp_pdf
    
    # Create 3-sticker PDF
    try:
        self.log(f"🏷️ Creating 3-sticker format...")
        
        output_path = create_3stickers_with_images(str(original_pdf))
        
        self.log(f"✅ 3-sticker PDF created: {output_path}")
        
        if messagebox.askyesno("Success", f"3-sticker PDF created!\n\n{output_path}\n\nOpen now?"):
            try:
                os.startfile(output_path)
            except:
                pass
    
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create 3-sticker PDF:\n\n{e}")
        self.log(f"✗ 3-sticker creation failed: {e}")


def create_single_sticker_pdf(self, position):
    """Create single sticker at specific position for selected voucher"""
    from pdf_to_single_sticker import create_single_sticker_at_position
    
    selection = self.shipments_tree.selection()
    
    if not selection:
        messagebox.showwarning("No Selection", "Please select a shipment first")
        return
    
    item = selection[0]
    values = self.shipments_tree.item(item, 'values')
    shipment_id = values[0]
    voucher_no = values[1]
    
    if not voucher_no or voucher_no == '-':
        messagebox.showerror("No Voucher", "This shipment doesn't have a voucher yet")
        return
    
    # Check if original PDF exists
    shipment = self.acs_db.get_shipment(shipment_id=shipment_id)
    original_pdf = None
    
    if shipment and shipment.get('pdf_path'):
        original_pdf = Path(shipment['pdf_path'])
        if not original_pdf.exists():
            original_pdf = None
    
    # If no PDF, download it first
    if not original_pdf:
        self.log(f"📄 Downloading voucher {voucher_no} first...")
        
        temp_pdf = self.pdf_today_folder / f"voucher_{voucher_no}_temp.pdf"
        
        result = self.acs_api.print_voucher(
            voucher_no=voucher_no,
            print_type=2,
            output_path=str(temp_pdf)
        )
        
        if not result['success']:
            error_msg = result.get('error', 'Unknown error')
            messagebox.showerror("Download Failed", f"Failed to download PDF:\n\n{error_msg}")
            return
        
        original_pdf = temp_pdf
    
    # Create single sticker PDF
    try:
        position_names = {1: "TOP", 2: "MIDDLE", 3: "BOTTOM"}
        self.log(f"🏷️ Creating {position_names[position]} position sticker...")
        
        output_path = create_single_sticker_at_position(str(original_pdf), position)
        
        self.log(f"✅ Sticker PDF created: {output_path}")
        
        if messagebox.askyesno("Success", 
            f"{position_names[position]} position sticker created!\n\n{output_path}\n\nOpen now?"):
            try:
                os.startfile(output_path)
            except:
                pass
    
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create sticker PDF:\n\n{e}")
        self.log(f"✗ Sticker creation failed: {e}")


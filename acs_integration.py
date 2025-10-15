"""
ACS Shipping Integration Tab - ALL ISSUES FIXED
✅ Enter key navigation in Manual Entry
✅ Edit orders before creating vouchers
✅ Better PDF creation with fallback methods
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime, date, time, timedelta
import threading
import os
from pathlib import Path

from acs_api import ACSCourierAPI, format_phone, validate_zipcode, split_address
from acs_database import ACSDatabase


class ACSShippingTab(ttk.Frame):
    """ACS Shipping Management Tab"""
    
    def __init__(self, parent, woocommerce_api, log_callback):
        """Initialize ACS shipping tab"""
        super().__init__(parent)
        
        self.woo = woocommerce_api
        self.log = log_callback
        
        # Initialize ACS components
        self.acs_api = ACSCourierAPI()
        self.acs_db = ACSDatabase()
        
        # Reminder settings
        self.pickup_time = time(10, 0)
        self.reminder_minutes = 15
        self.reminder_active = False
        
        # Store current pickup list number
        self.current_pickup_list_no = None
        
        # Setup PDF storage
        self.setup_pdf_storage()
        
        self.setup_ui()
        self.start_reminder_thread()
        
        if self.woo:
            self.log("✅ ACS Shipping module initialized with WooCommerce connection")
        else:
            self.log("⚠️ ACS Shipping initialized WITHOUT WooCommerce (manual mode only)")
    
    def setup_pdf_storage(self):
        """Create folder structure for storing voucher PDFs"""
        try:
            self.pdf_base_folder = Path("voucher_pdfs")
            self.pdf_base_folder.mkdir(exist_ok=True)
            
            today_str = date.today().strftime("%Y-%m-%d")
            self.pdf_today_folder = self.pdf_base_folder / today_str
            self.pdf_today_folder.mkdir(exist_ok=True)
            
            self.log(f"📂 PDF storage ready: {self.pdf_today_folder}")
        except Exception as e:
            self.log(f"⚠️ Warning: Could not create PDF folders: {e}")
            self.pdf_today_folder = Path(".")
    
    def get_pdf_folder_for_date(self, date_obj=None):
        """Get PDF folder for a specific date"""
        if date_obj is None:
            date_obj = date.today()
        
        date_str = date_obj.strftime("%Y-%m-%d")
        folder = self.pdf_base_folder / date_str
        folder.mkdir(exist_ok=True)
        return folder
    
    def setup_ui(self):
        """Setup main UI"""
        
        # Statistics panel at top
        self.create_stats_panel()
        
        # Sub-tabs
        self.sub_notebook = ttk.Notebook(self)
        self.sub_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Tab 1: All Shipments
        self.all_shipments_frame = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.all_shipments_frame, text="📦 All Shipments")
        self.create_all_shipments_tab()
        
        # Tab 2: E-Shop Orders
        self.eshop_orders_frame = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.eshop_orders_frame, text="🛒 E-Shop Orders")
        self.create_eshop_orders_tab()
        
        # Tab 3: Manual Entry
        self.manual_entry_frame = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.manual_entry_frame, text="➕ Manual Entry")
        self.create_manual_entry_tab()
        
        # Tab 4: Pickup Management
        self.pickup_frame = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.pickup_frame, text="📋 Pickup & Tracking")
        self.create_pickup_tab()
    
    def create_stats_panel(self):
        """Create statistics panel"""
        stats_frame = ttk.LabelFrame(self, text="📊 Today's Statistics", padding="10")
        stats_frame.pack(fill='x', padx=10, pady=10)
        
        # Variables
        self.stat_total = tk.StringVar(value="0")
        self.stat_eshop = tk.StringVar(value="0")
        self.stat_manual = tk.StringVar(value="0")
        self.stat_ready = tk.StringVar(value="0")
        self.stat_pickup = tk.StringVar(value="Next: 10:00")
        
        # Create stat labels
        cols = [
            ("Total Shipments:", self.stat_total),
            ("E-Shop:", self.stat_eshop),
            ("Manual:", self.stat_manual),
            ("Ready:", self.stat_ready),
            ("Next Pickup:", self.stat_pickup)
        ]
        
        for i, (label, var) in enumerate(cols):
            ttk.Label(stats_frame, text=label, font=('Arial', 10, 'bold')).grid(
                row=0, column=i*2, padx=5, sticky='e')
            ttk.Label(stats_frame, textvariable=var, font=('Arial', 10), 
                     foreground='blue').grid(row=0, column=i*2+1, padx=5, sticky='w')
        
        # Refresh button
        ttk.Button(stats_frame, text="🔄 Refresh", 
                  command=self.refresh_stats).grid(row=0, column=len(cols)*2, padx=20)
        
        self.refresh_stats()
    
    def refresh_stats(self):
        """Refresh statistics"""
        stats = self.acs_db.get_today_stats()
        
        self.stat_total.set(str(stats['total']))
        self.stat_eshop.set(str(stats['eshop']))
        self.stat_manual.set(str(stats['manual']))
        self.stat_ready.set(str(stats['ready']))
        
        now = datetime.now().time()
        if now < self.pickup_time:
            delta = datetime.combine(date.today(), self.pickup_time) - \
                    datetime.combine(date.today(), now)
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            self.stat_pickup.set(f"10:00 (in {hours}h {minutes}m)")
        else:
            self.stat_pickup.set("10:00 (tomorrow)")
    
    def create_voucher_with_auto_pdf(self, shipment_data, source, order_id=None):
        """Create voucher AND automatically save PDF - MULTIPLE METHODS"""
        try:
            # Step 1: Create voucher
            self.log(f"📝 Creating voucher...")
            result = self.acs_api.create_voucher(shipment_data)
            
            if not result['success']:
                return False, None, None, result.get('error', 'Unknown error')
            
            voucher_no = result['voucher_no']
            self.log(f"✅ Voucher created: {voucher_no}")
            
            # Step 2: Try to download PDF (with multiple fallback methods)
            pdf_path = None
            pdf_error = None
            
            # Method 1: Standard API call
            try:
                pdf_folder = self.get_pdf_folder_for_date()
                timestamp = datetime.now().strftime('%H%M%S')
                pdf_filename = f"voucher_{voucher_no}_{timestamp}.pdf"
                pdf_path = pdf_folder / pdf_filename
                
                self.log(f"📄 Method 1: Trying standard PDF download...")
                
                pdf_result = self.acs_api.print_voucher(
                    voucher_no=voucher_no,
                    print_type=2,  # Laser A4
                    output_path=str(pdf_path)
                )
                
                if pdf_result['success'] and pdf_path.exists() and pdf_path.stat().st_size > 0:
                    self.log(f"✅ PDF saved: {pdf_path.name}")
                else:
                    pdf_error = pdf_result.get('error', 'Empty PDF')
                    pdf_path = None
                    self.log(f"⚠️ Method 1 failed: {pdf_error}")
            
            except Exception as e:
                pdf_error = str(e)
                pdf_path = None
                self.log(f"⚠️ Method 1 exception: {e}")
            
            # Method 2: Wait and retry (sometimes PDFs need a moment)
            if not pdf_path:
                try:
                    self.log(f"📄 Method 2: Waiting 2 seconds and retrying...")
                    import time
                    time.sleep(2)
                    
                    pdf_result = self.acs_api.print_voucher(
                        voucher_no=voucher_no,
                        print_type=2,
                        output_path=str(pdf_folder / pdf_filename)
                    )
                    
                    if pdf_result['success']:
                        pdf_path = pdf_folder / pdf_filename
                        if pdf_path.exists() and pdf_path.stat().st_size > 0:
                            self.log(f"✅ PDF saved (method 2): {pdf_path.name}")
                        else:
                            pdf_path = None
                    
                except Exception as e:
                    self.log(f"⚠️ Method 2 exception: {e}")
            
            # Method 3: Try thermal printer format (print_type=1)
            if not pdf_path:
                try:
                    self.log(f"📄 Method 3: Trying thermal format...")
                    pdf_filename_thermal = f"voucher_{voucher_no}_{timestamp}_thermal.pdf"
                    
                    pdf_result = self.acs_api.print_voucher(
                        voucher_no=voucher_no,
                        print_type=1,  # Thermal
                        output_path=str(pdf_folder / pdf_filename_thermal)
                    )
                    
                    if pdf_result['success']:
                        pdf_path = pdf_folder / pdf_filename_thermal
                        if pdf_path.exists() and pdf_path.stat().st_size > 0:
                            self.log(f"✅ PDF saved (thermal): {pdf_path.name}")
                        else:
                            pdf_path = None
                
                except Exception as e:
                    self.log(f"⚠️ Method 3 exception: {e}")
            
            # Final status
            if not pdf_path:
                self.log(f"⚠️ All PDF methods failed. Error: {pdf_error}")
                self.log(f"💡 You can download PDF later from 'All Shipments' tab")
            
            # Step 3: Save to database
            self.acs_db.add_shipment({
                'voucher_no': voucher_no,
                'source': source,
                'woocommerce_order_id': order_id,
                'pdf_path': str(pdf_path) if pdf_path else None,
                'recipient_name': shipment_data['recipient_name'],
                'recipient_address': shipment_data['recipient_address'],
                'recipient_city': shipment_data['recipient_region'],
                'recipient_zipcode': shipment_data['recipient_zipcode'],
                'recipient_phone': shipment_data['recipient_phone'],
                'recipient_email': shipment_data.get('recipient_email', ''),
                'weight': shipment_data.get('weight', 1.0),
                'pieces': shipment_data.get('pieces', 1),
                'cod_amount': shipment_data.get('cod_amount', 0),
                'notes': shipment_data.get('delivery_notes', ''),
                'status': 'READY'
            })
            
            return True, voucher_no, str(pdf_path) if pdf_path else None, None
        
        except Exception as e:
            return False, None, None, str(e)
    
    def create_all_shipments_tab(self):
        """Create all shipments view"""
        
        # Controls
        control_frame = ttk.Frame(self.all_shipments_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="All Shipments", 
                 font=('Arial', 12, 'bold')).pack(side='left')
        
        ttk.Button(control_frame, text="🔄 Refresh", 
                  command=self.load_all_shipments).pack(side='right', padx=5)
        ttk.Button(control_frame, text="📄 Download Voucher PDF", 
                  command=self.export_selected_voucher_pdf).pack(side='right', padx=5)
        
        # Filter frame
        filter_frame = ttk.Frame(self.all_shipments_frame)
        filter_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side='left', padx=5)
        
        self.filter_source = tk.StringVar(value="ALL")
        ttk.Radiobutton(filter_frame, text="All", variable=self.filter_source, 
                       value="ALL", command=self.load_all_shipments).pack(side='left')
        ttk.Radiobutton(filter_frame, text="E-Shop", variable=self.filter_source, 
                       value="ESHOP", command=self.load_all_shipments).pack(side='left')
        ttk.Radiobutton(filter_frame, text="Manual", variable=self.filter_source, 
                       value="MANUAL", command=self.load_all_shipments).pack(side='left')
        
        ttk.Label(filter_frame, text="  Date:").pack(side='left', padx=(20, 5))
        self.filter_days = tk.StringVar(value="7")
        ttk.Combobox(filter_frame, textvariable=self.filter_days, 
                    values=["1", "7", "30", "90"], width=5,
                    state='readonly').pack(side='left')
        ttk.Button(filter_frame, text="Apply", 
                  command=self.load_all_shipments).pack(side='left', padx=5)
        
        # Shipments tree
        tree_frame = ttk.Frame(self.all_shipments_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('ID', 'Voucher', 'Source', 'Date', 'Recipient', 
                  'City', 'ZIP', 'COD', 'PDF', 'Status')
        self.shipments_tree = ttk.Treeview(tree_frame, columns=columns, 
                                          show='headings', height=20)
        
        widths = {'ID': 50, 'Voucher': 100, 'Source': 70, 'Date': 90,
                 'Recipient': 150, 'City': 120, 'ZIP': 60, 'COD': 70, 'PDF': 50, 'Status': 100}
        
        for col in columns:
            self.shipments_tree.heading(col, text=col)
            self.shipments_tree.column(col, width=widths.get(col, 100))
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', 
                                 command=self.shipments_tree.yview)
        self.shipments_tree.configure(yscrollcommand=scrollbar.set)
        
        self.shipments_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.shipments_tree.bind('<Double-Button-1>', self.show_shipment_details)
        
        self.load_all_shipments()
    
    def load_all_shipments(self):
        """Load all shipments"""
        for item in self.shipments_tree.get_children():
            self.shipments_tree.delete(item)
        
        filters = {}
        
        source = self.filter_source.get()
        if source != "ALL":
            filters['source'] = source
        
        try:
            days = int(self.filter_days.get())
            filters['date_from'] = date.today() - timedelta(days=days)
        except:
            pass
        
        shipments = self.acs_db.get_all_shipments(filters)
        
        for ship in shipments:
            source_icon = "🛒" if ship['source'] == 'ESHOP' else "📝"
            cod = f"€{ship['cod_amount']:.2f}" if ship['cod_amount'] else "-"
            created = ship['created_date'].split()[0] if ship['created_date'] else ""
            
            pdf_status = "✅" if ship.get('pdf_path') else "❌"
            
            status_map = {
                'DRAFT': '📝',
                'READY': '✅',
                'PICKED_UP': '📦',
                'IN_TRANSIT': '🚚',
                'DELIVERED': '✔'
            }
            status = f"{status_map.get(ship['status'], '•')} {ship['status']}"
            
            self.shipments_tree.insert('', 'end', values=(
                ship['id'],
                ship['voucher_no'] or '-',
                f"{source_icon}{ship['source']}",
                created,
                ship['recipient_name'][:20],
                ship['recipient_city'][:15],
                ship['recipient_zipcode'],
                cod,
                pdf_status,
                status
            ), tags=(ship['status'],))
        
        self.shipments_tree.tag_configure('DRAFT', background='#FFE4B5')
        self.shipments_tree.tag_configure('READY', background='#90EE90')
        self.shipments_tree.tag_configure('PICKED_UP', background='#87CEEB')
        
        self.log(f"Loaded {len(shipments)} shipments")
    
    def export_selected_voucher_pdf(self):
        """Export selected voucher PDF"""
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
        
        # Check if PDF already saved
        shipment = self.acs_db.get_shipment(shipment_id=shipment_id)
        if shipment and shipment.get('pdf_path'):
            existing_pdf = Path(shipment['pdf_path'])
            if existing_pdf.exists():
                if messagebox.askyesno("PDF Already Saved",
                    f"PDF already saved:\n\n{existing_pdf}\n\nOpen it now?"):
                    try:
                        os.startfile(str(existing_pdf))
                    except:
                        pass
                    return
        
        # Download PDF
        default_filename = f"voucher_{voucher_no}_{date.today().strftime('%Y%m%d')}.pdf"
        
        filename = filedialog.asksaveasfilename(
            title="Save Voucher PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_filename
        )
        
        if not filename:
            return
        
        self.log(f"📄 Downloading voucher {voucher_no}...")
        
        result = self.acs_api.print_voucher(
            voucher_no=voucher_no,
            print_type=2,
            output_path=filename
        )
        
        if result['success']:
            self.log(f"✅ PDF saved: {filename}")
            self.acs_db.update_shipment(shipment_id, {'pdf_path': filename})
            self.load_all_shipments()
            
            if messagebox.askyesno("Success", f"PDF saved!\n\n{filename}\n\nOpen now?"):
                try:
                    os.startfile(filename)
                except:
                    pass
        else:
            error_msg = result.get('error', 'Unknown error')
            messagebox.showerror("Download Failed", f"Failed to download PDF:\n\n{error_msg}")
            self.log(f"✗ PDF download failed: {error_msg}")
    
    def create_eshop_orders_tab(self):
        """Create E-Shop orders tab WITH EDIT FUNCTIONALITY"""
        
        # Controls
        control_frame = ttk.Frame(self.eshop_orders_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="WooCommerce Orders → ACS Vouchers", 
                 font=('Arial', 12, 'bold')).pack(side='left')
        
        ttk.Button(control_frame, text="🔄 Sync Orders", 
                  command=self.sync_woocommerce_orders).pack(side='right', padx=5)
        ttk.Button(control_frame, text="📝 Create Vouchers for Selected", 
                  command=self.create_vouchers_from_orders).pack(side='right', padx=5)
        ttk.Button(control_frame, text="✏️ Edit & Create Voucher", 
                  command=self.edit_and_create_voucher).pack(side='right', padx=5)
        
        # Orders tree
        tree_frame = ttk.Frame(self.eshop_orders_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('Select', 'Order ID', 'Date', 'Customer', 'Phone', 
                  'City', 'ZIP', 'Total', 'Voucher')
        self.orders_tree = ttk.Treeview(tree_frame, columns=columns, 
                                       show='tree headings', height=20)
        
        for col in columns:
            self.orders_tree.heading(col, text=col)
        
        self.orders_tree.column('#0', width=30)
        self.orders_tree.column('Select', width=50)
        self.orders_tree.column('Order ID', width=80)
        self.orders_tree.column('Date', width=90)
        self.orders_tree.column('Customer', width=150)
        self.orders_tree.column('Phone', width=100)
        self.orders_tree.column('City', width=120)
        self.orders_tree.column('ZIP', width=60)
        self.orders_tree.column('Total', width=70)
        self.orders_tree.column('Voucher', width=100)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', 
                                 command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=scrollbar.set)
        
        self.orders_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.orders_tree.bind('<Button-1>', self.toggle_order_selection)
    
    def edit_and_create_voucher(self):
        """NEW: Edit order details before creating voucher"""
        selection = self.orders_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select ONE order to edit")
            return
        
        if len(selection) > 1:
            messagebox.showwarning("Too Many", "Please select only ONE order to edit")
            return
        
        # Get order details
        item = selection[0]
        values = self.orders_tree.item(item, 'values')
        order_id = values[1]
        
        # Get full order from WooCommerce
        try:
            all_orders = self.woo.get_all_orders()
            order = next((o for o in all_orders if str(o['id']) == str(order_id)), None)
            
            if not order:
                messagebox.showerror("Error", f"Order #{order_id} not found")
                return
            
            # Open edit dialog
            self.open_order_edit_dialog(order)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load order:\n\n{e}")
    
    def open_order_edit_dialog(self, order):
        """Open dialog to edit order details before creating voucher"""
        dialog = tk.Toplevel(self.master)
        dialog.title(f"Edit Order #{order['id']} → Create Voucher")
        dialog.geometry("600x700")
        dialog.grab_set()
        
        # Create form
        form_frame = ttk.LabelFrame(dialog, text="Edit Shipping Details", padding="20")
        form_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        billing = order['billing']
        street, number = split_address(billing['address_1'])
        
        # Fields
        fields = {}
        field_defs = [
            ('Recipient Name *', 'recipient_name', f"{billing['first_name']} {billing['last_name']}"),
            ('Address * (street)', 'recipient_address', street),
            ('Number', 'recipient_address_number', number or ''),
            ('City *', 'recipient_region', billing['city']),
            ('Zipcode * (5 digits)', 'recipient_zipcode', billing['postcode']),
            ('Phone * (10 digits)', 'recipient_phone', billing.get('phone', '')),
            ('Email', 'recipient_email', billing.get('email', '')),
            ('Weight (kg)', 'weight', '1.0'),
            ('COD Amount (€)', 'cod_amount', order['total'] if order['payment_method'] == 'cod' else '0'),
            ('Notes', 'notes', f"WooCommerce Order #{order['id']}")
        ]
        
        for i, (label, field, default) in enumerate(field_defs):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, sticky='w', pady=5, padx=5)
            
            if field == 'notes':
                entry = tk.Text(form_frame, height=3, width=50)
                entry.insert('1.0', default)
            else:
                entry = ttk.Entry(form_frame, width=50)
                entry.insert(0, default)
            
            entry.grid(row=i, column=1, pady=5, padx=5)
            fields[field] = entry
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def create_voucher():
            # Get edited values
            data = {}
            for field, widget in fields.items():
                if isinstance(widget, tk.Text):
                    data[field] = widget.get('1.0', 'end-1c').strip()
                else:
                    data[field] = widget.get().strip()
            
            # Validate
            if not all([data.get('recipient_name'), data.get('recipient_address'),
                       data.get('recipient_region'), data.get('recipient_zipcode'),
                       data.get('recipient_phone')]):
                messagebox.showerror("Missing Fields", "Please fill all required fields (*)")
                return
            
            # Format and create
            try:
                api_data = {
                    'recipient_name': data['recipient_name'],
                    'recipient_address': data['recipient_address'],
                    'recipient_address_number': data.get('recipient_address_number', ''),
                    'recipient_region': data['recipient_region'],
                    'recipient_zipcode': data['recipient_zipcode'],
                    'recipient_phone': format_phone(data['recipient_phone']),
                    'recipient_cell_phone': format_phone(data['recipient_phone']),
                    'recipient_email': data.get('recipient_email', ''),
                    'weight': float(data.get('weight', 1.0)),
                    'cod_amount': float(data.get('cod_amount', 0)),
                    'reference1': f"Order #{order['id']}",
                    'delivery_notes': data.get('notes', '')
                }
                
                success, voucher_no, pdf_path, error = self.create_voucher_with_auto_pdf(
                    api_data,
                    source='ESHOP',
                    order_id=order['id']
                )
                
                if success:
                    message = f"✅ Voucher created!\n\nVoucher: {voucher_no}\n\n"
                    if pdf_path:
                        message += f"PDF saved: {Path(pdf_path).name}"
                    
                    messagebox.showinfo("Success", message)
                    dialog.destroy()
                    self.refresh_stats()
                    self.load_all_shipments()
                    self.sync_woocommerce_orders()
                else:
                    messagebox.showerror("Error", f"Failed:\n\n{error}")
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create voucher:\n\n{e}")
        
        ttk.Button(button_frame, text="✅ Create Voucher", command=create_voucher).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
    
    def sync_woocommerce_orders(self):
        """Sync WooCommerce orders"""
        if not self.woo:
            messagebox.showerror("WooCommerce Not Connected", "WooCommerce API is not connected!")
            return
        
        self.log("🔄 Syncing WooCommerce orders...")
        
        try:
            all_orders = self.woo.get_all_orders()
            orders = [o for o in all_orders if o['status'] == 'processing']
            
            for item in self.orders_tree.get_children():
                self.orders_tree.delete(item)
            
            for order in orders:
                billing = order.get('billing', {})
                
                existing = self.acs_db.get_all_shipments({
                    'woocommerce_order_id': order['id']
                })
                
                voucher_status = "✅ Created" if existing else "Pending"
                
                self.orders_tree.insert('', 'end', text='☐', values=(
                    '',
                    order['id'],
                    order['date_created'].split('T')[0],
                    f"{billing.get('first_name', '')} {billing.get('last_name', '')}",
                    billing.get('phone', ''),
                    billing.get('city', ''),
                    billing.get('postcode', ''),
                    f"€{order['total']}",
                    voucher_status
                ), tags=('unchecked',))
            
            self.log(f"✅ Synced {len(orders)} orders")
            messagebox.showinfo("Success", f"Loaded {len(orders)} orders")
            
        except Exception as e:
            self.log(f"✗ Error: {e}")
            messagebox.showerror("Error", f"Failed to sync:\n\n{e}")
    
    def toggle_order_selection(self, event):
        """Toggle order checkbox"""
        region = self.orders_tree.identify_region(event.x, event.y)
        if region == "tree":
            item = self.orders_tree.identify_row(event.y)
            if item:
                current_text = self.orders_tree.item(item, 'text')
                new_text = '☑' if current_text == '☐' else '☐'
                self.orders_tree.item(item, text=new_text)
    
    def create_vouchers_from_orders(self):
        """Create vouchers from selected orders"""
        selected = []
        
        for item in self.orders_tree.get_children():
            if self.orders_tree.item(item, 'text') == '☑':
                selected.append(item)
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select orders")
            return
        
        if not messagebox.askyesno("Confirm", f"Create {len(selected)} vouchers?"):
            return
        
        self.log(f"Creating {len(selected)} vouchers...")
        
        success_count = 0
        errors = []
        
        for item in selected:
            values = self.orders_tree.item(item, 'values')
            order_id = values[1]
            
            try:
                all_orders = self.woo.get_all_orders()
                order = next((o for o in all_orders if str(o['id']) == str(order_id)), None)
                
                if order:
                    result = self.create_voucher_from_order(order)
                    if result:
                        success_count += 1
                        self.orders_tree.item(item, values=(*values[:-1], "✅ Created"))
                    else:
                        errors.append(f"Order #{order_id}: Failed")
                else:
                    errors.append(f"Order #{order_id}: Not found")
                    
            except Exception as e:
                errors.append(f"Order #{order_id}: {str(e)}")
        
        summary = f"✅ Created {success_count}/{len(selected)} vouchers"
        if errors:
            summary += f"\n\n⚠️ Errors:\n" + "\n".join(errors[:5])
        
        messagebox.showinfo("Complete", summary)
        self.refresh_stats()
        self.load_all_shipments()
    
    def create_voucher_from_order(self, order):
        """Create voucher from order"""
        try:
            billing = order['billing']
            street, number = split_address(billing['address_1'])
            
            shipment_data = {
                'recipient_name': f"{billing['first_name']} {billing['last_name']}",
                'recipient_address': street,
                'recipient_address_number': number or '',
                'recipient_region': billing['city'],
                'recipient_zipcode': billing['postcode'],
                'recipient_phone': format_phone(billing.get('phone', '')),
                'recipient_cell_phone': format_phone(billing.get('phone', '')),
                'recipient_email': billing.get('email', ''),
                'weight': 1.0,
                'cod_amount': float(order['total']) if order['payment_method'] == 'cod' else 0,
                'reference1': f"Order #{order['id']}",
                'delivery_notes': f"WooCommerce Order #{order['id']}"
            }
            
            success, voucher_no, pdf_path, error = self.create_voucher_with_auto_pdf(
                shipment_data,
                source='ESHOP',
                order_id=order['id']
            )
            
            if success:
                self.log(f"✅ Voucher {voucher_no} for order #{order['id']}")
                return True
            else:
                self.log(f"✗ Failed order #{order['id']}: {error}")
                return False
                
        except Exception as e:
            self.log(f"✗ Error: {e}")
            return False
    
    def create_manual_entry_tab(self):
        """Create manual entry tab WITH ENTER KEY NAVIGATION"""
        
        ttk.Label(self.manual_entry_frame, 
                 text="Manual Shipment Entry (for phone orders)", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        form_frame = ttk.LabelFrame(self.manual_entry_frame, 
                                   text="Shipment Details", padding="20")
        form_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.manual_fields = {}
        
        fields = [
            ('Recipient Name *', 'recipient_name'),
            ('Address * (street only)', 'recipient_address'),
            ('Number', 'recipient_address_number'),
            ('City/Region *', 'recipient_region'),
            ('Zipcode * (5 digits)', 'recipient_zipcode'),
            ('Phone * (10 digits)', 'recipient_phone'),
            ('Email', 'recipient_email'),
            ('Weight (kg)', 'weight'),
            ('COD Amount (€)', 'cod_amount'),
            ('Reference/Notes', 'notes')
        ]
        
        # Create fields with Enter key navigation
        for i, (label, field) in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, 
                                                   sticky='w', pady=5, padx=5)
            
            if field == 'notes':
                entry = tk.Text(form_frame, height=3, width=50)
            else:
                entry = ttk.Entry(form_frame, width=50)
            
            entry.grid(row=i, column=1, pady=5, padx=5)
            self.manual_fields[field] = entry
            
            # Bind Enter key to move to next field (except for Text widget)
            if not isinstance(entry, tk.Text):
                def make_enter_handler(current_index, fields_list):
                    def handler(event):
                        # Move to next field
                        next_index = current_index + 1
                        if next_index < len(fields_list):
                            next_field = fields_list[next_index][1]
                            self.manual_fields[next_field].focus_set()
                        return "break"  # Prevent default Enter behavior
                    return handler
                
                entry.bind('<Return>', make_enter_handler(i, fields))
        
        # Buttons
        button_frame = ttk.Frame(self.manual_entry_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Save as Draft", 
                  command=lambda: self.save_manual_entry(create_voucher=False)).pack(
                      side='left', padx=5)
        ttk.Button(button_frame, text="✅ Create Voucher + Auto Save PDF", 
                  command=lambda: self.save_manual_entry(create_voucher=True)).pack(
                      side='left', padx=5)
        ttk.Button(button_frame, text="Clear Form", 
                  command=self.clear_manual_form).pack(side='left', padx=5)
        
        # Focus on first field
        self.manual_fields['recipient_name'].focus_set()
    
    def save_manual_entry(self, create_voucher=False):
        """Save manual entry"""
        data = {}
        for field, widget in self.manual_fields.items():
            if isinstance(widget, tk.Text):
                data[field] = widget.get('1.0', 'end-1c').strip()
            else:
                data[field] = widget.get().strip()
        
        required = {
            'recipient_name': 'Recipient Name',
            'recipient_address': 'Street Address',
            'recipient_region': 'City/Region',
            'recipient_zipcode': 'Zipcode',
            'recipient_phone': 'Phone'
        }
        
        for field, label in required.items():
            if not data.get(field):
                messagebox.showerror("Missing Field", f"Please fill: {label}")
                return
        
        if not validate_zipcode(data['recipient_zipcode']):
            messagebox.showerror("Invalid Zipcode", "Zipcode must be 5 digits")
            return
        
        phone = format_phone(data['recipient_phone'])
        if len(phone) != 10:
            messagebox.showerror("Invalid Phone", "Phone must be 10 digits")
            return
        
        data['recipient_phone'] = phone
        data['recipient_cell_phone'] = phone
        
        try:
            data['weight'] = float(data.get('weight') or 1.0)
            data['cod_amount'] = float(data.get('cod_amount') or 0)
        except ValueError:
            messagebox.showerror("Invalid Number", "Weight and COD must be numbers")
            return
        
        if create_voucher:
            self.log("📝 Creating manual voucher...")
            
            api_data = {
                'recipient_name': data['recipient_name'],
                'recipient_address': data['recipient_address'],
                'recipient_address_number': data.get('recipient_address_number', ''),
                'recipient_region': data['recipient_region'],
                'recipient_zipcode': data['recipient_zipcode'],
                'recipient_phone': data['recipient_phone'],
                'recipient_cell_phone': data['recipient_cell_phone'],
                'recipient_email': data.get('recipient_email', ''),
                'weight': data['weight'],
                'cod_amount': data['cod_amount'],
                'reference1': data.get('notes', ''),
                'delivery_notes': data.get('notes', '')
            }
            
            success, voucher_no, pdf_path, error = self.create_voucher_with_auto_pdf(
                api_data, 
                source='MANUAL'
            )
            
            if success:
                message = f"✅ Voucher created!\n\nVoucher: {voucher_no}\n\n"
                
                if pdf_path:
                    message += f"PDF saved: {Path(pdf_path).name}\n\nOpen now?"
                    
                    if messagebox.askyesno("Success", message):
                        try:
                            os.startfile(pdf_path)
                        except:
                            pass
                else:
                    message += "⚠️ PDF download failed.\nDownload from 'All Shipments' tab."
                    messagebox.showwarning("Partial Success", message)
                
                self.clear_manual_form()
                self.refresh_stats()
                self.load_all_shipments()
            else:
                messagebox.showerror("Error", f"Failed:\n\n{error}")
        else:
            # Save as draft
            db_data = {
                'voucher_no': None,
                'source': 'MANUAL',
                'woocommerce_order_id': None,
                'manual_reference': data.get('notes', ''),
                'recipient_name': data['recipient_name'],
                'recipient_address': data['recipient_address'],
                'recipient_city': data['recipient_region'],
                'recipient_zipcode': data['recipient_zipcode'],
                'recipient_phone': data['recipient_phone'],
                'recipient_email': data.get('recipient_email', ''),
                'weight': data.get('weight', 1.0),
                'pieces': 1,
                'cod_amount': data.get('cod_amount', 0),
                'notes': data.get('notes', ''),
                'status': 'DRAFT'
            }
            
            self.acs_db.add_shipment(db_data)
            messagebox.showinfo("Saved", "Entry saved as draft")
            self.clear_manual_form()
            self.load_all_shipments()
    
    def clear_manual_form(self):
        """Clear manual entry form"""
        for widget in self.manual_fields.values():
            if isinstance(widget, tk.Text):
                widget.delete('1.0', 'end')
            else:
                widget.delete(0, 'end')
        
        # Focus back to first field
        self.manual_fields['recipient_name'].focus_set()
    
    def create_pickup_tab(self):
        """Create pickup management tab"""
        
        control_frame = ttk.Frame(self.pickup_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="Pickup Management & Tracking", 
                 font=('Arial', 12, 'bold')).pack(side='left')
        
        ttk.Button(control_frame, text="📋 Create Pickup List", 
                  command=self.create_pickup_list).pack(side='right', padx=5)
        ttk.Button(control_frame, text="📄 Export Pickup List PDF", 
                  command=self.export_pickup_list_pdf).pack(side='right', padx=5)
        
        info_frame = ttk.LabelFrame(self.pickup_frame, 
                                   text="Pickup Information", padding="10")
        info_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(info_frame, text="Daily Pickup Time: 10:00", 
                 font=('Arial', 10, 'bold')).pack(anchor='w')
        ttk.Label(info_frame, text="Usually ACS pickup guy creates the list").pack(anchor='w')
        
        self.pickup_list_label = ttk.Label(info_frame, text="No pickup list created today", 
                                          foreground='red')
        self.pickup_list_label.pack(anchor='w', pady=5)
    
    def create_pickup_list(self):
        """Create pickup list"""
        stats = self.acs_db.get_today_stats()
        
        if stats['total'] == 0:
            messagebox.showwarning("No Shipments", "No shipments for today")
            return
        
        if not messagebox.askyesno("Confirm", f"Create pickup list for {stats['total']} shipments?"):
            return
        
        self.log("📋 Creating pickup list...")
        
        result = self.acs_api.create_pickup_list()
        
        if result['success']:
            pickup_list_no = result['pickup_list_no']
            self.current_pickup_list_no = pickup_list_no
            
            list_id, _ = self.acs_db.create_pickup_list()
            
            self.log(f"✅ Pickup list: {pickup_list_no}")
            self.pickup_list_label.config(
                text=f"✅ Today's list: {pickup_list_no}",
                foreground='green'
            )
            
            messagebox.showinfo("Success", f"Pickup list created!\n\n{pickup_list_no}")
            self.refresh_stats()
        else:
            error_msg = result.get('error', 'Unknown error')
            messagebox.showerror("Error", f"Failed:\n\n{error_msg}")
    
    def export_pickup_list_pdf(self):
        """Export pickup list PDF"""
        if not self.current_pickup_list_no:
            messagebox.showwarning("No List", "No pickup list created yet")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Save Pickup List PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"pickup_list_{self.current_pickup_list_no}.pdf"
        )
        
        if not filename:
            return
        
        result = self.acs_api.print_pickup_list(
            mass_number=self.current_pickup_list_no,
            pickup_date=date.today().strftime('%Y-%m-%d'),
            output_path=filename
        )
        
        if result['success']:
            messagebox.showinfo("Success", f"Saved to:\n{filename}")
            try:
                os.startfile(filename)
            except:
                pass
        else:
            messagebox.showerror("Error", f"Failed:\n\n{result.get('error')}")
    
    def show_shipment_details(self, event):
        """Show shipment details"""
        selection = self.shipments_tree.selection()
        if not selection:
            return
        
        item = self.shipments_tree.item(selection[0])
        ship_id = item['values'][0]
        
        shipment = self.acs_db.get_shipment(shipment_id=ship_id)
        
        if shipment:
            details = f"SHIPMENT #{shipment['id']}\n{'='*50}\n\n"
            details += f"Voucher: {shipment['voucher_no'] or 'Not created'}\n"
            details += f"Source: {shipment['source']}\n"
            details += f"Status: {shipment['status']}\n"
            
            if shipment.get('pdf_path'):
                details += f"PDF: ✅ {Path(shipment['pdf_path']).name}\n"
            else:
                details += f"PDF: ❌ Not saved\n"
            
            details += f"\nRecipient:\n"
            details += f"  {shipment['recipient_name']}\n"
            details += f"  {shipment['recipient_address']}\n"
            details += f"  {shipment['recipient_zipcode']} {shipment['recipient_city']}\n"
            details += f"  Phone: {shipment['recipient_phone']}\n"
            
            messagebox.showinfo(f"Shipment #{ship_id}", details)
    
    def start_reminder_thread(self):
        """Start reminder thread"""
        def check_reminders():
            import time
            while True:
                now = datetime.now()
                pickup_datetime = datetime.combine(date.today(), self.pickup_time)
                reminder_datetime = pickup_datetime - timedelta(minutes=self.reminder_minutes)
                
                if (reminder_datetime <= now < pickup_datetime and not self.reminder_active):
                    self.show_pickup_reminder()
                    self.reminder_active = True
                elif now >= pickup_datetime:
                    self.reminder_active = False
                
                time.sleep(60)
        
        thread = threading.Thread(target=check_reminders, daemon=True)
        thread.start()
    
    def show_pickup_reminder(self):
        """Show pickup reminder"""
        stats = self.acs_db.get_today_stats()
        
        if stats['total'] == 0:
            return
        
        reminder = tk.Toplevel(self.master)
        reminder.title("📢 Pickup Reminder")
        reminder.geometry("400x200")
        reminder.grab_set()
        
        frame = ttk.Frame(reminder, padding="20")
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text="📢 COURIER PICKUP REMINDER", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        ttk.Label(frame, text=f"Pickup time: 10:00", 
                 font=('Arial', 11)).pack(pady=5)
        ttk.Label(frame, text=f"Total shipments: {stats['total']}", 
                 font=('Arial', 11)).pack(pady=5)
        
        ttk.Button(frame, text="✅ Ready", command=reminder.destroy).pack(pady=10)
        
        reminder.bell()
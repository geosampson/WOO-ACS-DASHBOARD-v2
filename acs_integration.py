"""
ACS Shipping Integration Tab - FINAL CORRECTED VERSION
Adds ACS shipping management to existing WooCommerce dashboard

FINAL FIXES:
✅ Correct print_voucher() call with proper parameters
✅ Correct print_pickup_list() call with proper parameters  
✅ Proper address handling with split_address()
✅ Correct field mapping (recipient_region vs recipient_city)
✅ Better validation and error messages
✅ Loading indicators for long operations
✅ Current pickup list tracking
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime, date, time, timedelta
import threading
from typing import Dict, List, Optional
import os

from acs_api import ACSCourierAPI, format_phone, validate_zipcode, split_address
from acs_database import ACSDatabase


class ACSShippingTab(ttk.Frame):
    """ACS Shipping Management Tab"""
    
    def __init__(self, parent, woocommerce_api, log_callback):
        """
        Initialize ACS shipping tab
        
        Args:
            parent: Parent notebook
            woocommerce_api: WooCommerceAPI instance
            log_callback: Function to log messages
        """
        super().__init__(parent)
        
        self.woo = woocommerce_api
        self.log = log_callback
        
        # Initialize ACS components
        self.acs_api = ACSCourierAPI()
        self.acs_db = ACSDatabase()
        
        # Reminder settings
        self.pickup_time = time(10, 0)  # 10:00
        self.reminder_minutes = 15  # Remind 15 minutes before
        self.reminder_active = False
        
        # Store current pickup list number
        self.current_pickup_list_no = None
        
        self.setup_ui()
        self.start_reminder_thread()
        
        self.log("✅ ACS Shipping module initialized")
    
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
        
        # Initial load
        self.refresh_stats()
    
    def refresh_stats(self):
        """Refresh statistics"""
        stats = self.acs_db.get_today_stats()
        
        self.stat_total.set(str(stats['total']))
        self.stat_eshop.set(str(stats['eshop']))
        self.stat_manual.set(str(stats['manual']))
        self.stat_ready.set(str(stats['ready']))
        
        # Calculate time to next pickup
        now = datetime.now().time()
        if now < self.pickup_time:
            delta = datetime.combine(date.today(), self.pickup_time) - \
                    datetime.combine(date.today(), now)
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            self.stat_pickup.set(f"10:00 (in {hours}h {minutes}m)")
        else:
            self.stat_pickup.set("10:00 (tomorrow)")
    
    def create_all_shipments_tab(self):
        """Create all shipments view"""
        
        # Controls
        control_frame = ttk.Frame(self.all_shipments_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="All Shipments", 
                 font=('Arial', 12, 'bold')).pack(side='left')
        
        ttk.Button(control_frame, text="🔄 Refresh", 
                  command=self.load_all_shipments).pack(side='right', padx=5)
        ttk.Button(control_frame, text="📊 Export Excel", 
                  command=self.export_shipments).pack(side='right', padx=5)
        ttk.Button(control_frame, text="📄 Export Voucher PDF", 
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
                  'City', 'ZIP', 'COD', 'Status')
        self.shipments_tree = ttk.Treeview(tree_frame, columns=columns, 
                                          show='headings', height=20)
        
        widths = {'ID': 50, 'Voucher': 100, 'Source': 70, 'Date': 90,
                 'Recipient': 150, 'City': 120, 'ZIP': 60, 'COD': 70, 'Status': 100}
        
        for col in columns:
            self.shipments_tree.heading(col, text=col)
            self.shipments_tree.column(col, width=widths.get(col, 100))
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', 
                                 command=self.shipments_tree.yview)
        self.shipments_tree.configure(yscrollcommand=scrollbar.set)
        
        self.shipments_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Double-click to see details
        self.shipments_tree.bind('<Double-Button-1>', self.show_shipment_details)
        
        # Load initial data
        self.load_all_shipments()
    
    def load_all_shipments(self):
        """Load all shipments"""
        # Clear tree
        for item in self.shipments_tree.get_children():
            self.shipments_tree.delete(item)
        
        # Build filters
        filters = {}
        
        source = self.filter_source.get()
        if source != "ALL":
            filters['source'] = source
        
        try:
            days = int(self.filter_days.get())
            filters['date_from'] = date.today() - timedelta(days=days)
        except:
            pass
        
        # Get shipments
        shipments = self.acs_db.get_all_shipments(filters)
        
        for ship in shipments:
            # Format values
            source_icon = "🛒" if ship['source'] == 'ESHOP' else "📝"
            cod = f"€{ship['cod_amount']:.2f}" if ship['cod_amount'] else "-"
            created = ship['created_date'].split()[0] if ship['created_date'] else ""
            
            # Status emoji
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
                status
            ), tags=(ship['status'],))
        
        # Color coding
        self.shipments_tree.tag_configure('DRAFT', background='#FFE4B5')
        self.shipments_tree.tag_configure('READY', background='#90EE90')
        self.shipments_tree.tag_configure('PICKED_UP', background='#87CEEB')
        
        self.log(f"Loaded {len(shipments)} shipments")
    
    def export_selected_voucher_pdf(self):
        """Export selected voucher as PDF"""
        selection = self.shipments_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", 
                "Please select a shipment with a voucher number")
            return
        
        # Get voucher number from selected row
        item = selection[0]
        values = self.shipments_tree.item(item, 'values')
        voucher_no = values[1]  # Column index for Voucher
        
        if not voucher_no or voucher_no == '-':
            messagebox.showerror("No Voucher", 
                "This shipment doesn't have a voucher yet.\n\n" +
                "Please create the voucher first.")
            return
        
        # Ask where to save
        default_filename = f"voucher_{voucher_no}_{date.today().strftime('%Y%m%d')}.pdf"
        
        filename = filedialog.asksaveasfilename(
            title="Save Voucher PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=default_filename
        )
        
        if not filename:
            return  # User cancelled
        
        # Show progress
        self.log(f"📄 Exporting voucher {voucher_no} to PDF...")
        
        # Export PDF with CORRECT parameters!
        result = self.acs_api.print_voucher(
            voucher_no=voucher_no,
            print_type=2,  # 2 = laser A4, 1 = thermal
            output_path=filename
        )
        
        if result['success']:
            self.log(f"✅ Voucher PDF saved: {filename}")
            
            # Ask if user wants to open it
            if messagebox.askyesno("Success", 
                f"✅ Voucher PDF saved!\n\n{filename}\n\nOpen the file now?"):
                try:
                    import os
                    os.startfile(filename)  # Windows
                except:
                    try:
                        import subprocess
                        subprocess.call(['xdg-open', filename])  # Linux
                    except:
                        pass
        else:
            error_msg = result.get('error', 'Unknown error')
            self.log(f"✗ Failed to export voucher: {error_msg}")
            messagebox.showerror("Export Failed", 
                f"Failed to export voucher PDF:\n\n{error_msg}")
    
    def create_eshop_orders_tab(self):
        """Create E-Shop orders tab"""
        
        # Controls
        control_frame = ttk.Frame(self.eshop_orders_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="WooCommerce Orders → ACS Vouchers", 
                 font=('Arial', 12, 'bold')).pack(side='left')
        
        ttk.Button(control_frame, text="🔄 Sync Orders", 
                  command=self.sync_woocommerce_orders).pack(side='right', padx=5)
        ttk.Button(control_frame, text="📝 Create Vouchers for Selected", 
                  command=self.create_vouchers_from_orders).pack(side='right', padx=5)
        
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
        
        # Checkboxes for selection
        self.orders_tree.bind('<Button-1>', self.toggle_order_selection)
    
    def sync_woocommerce_orders(self):
        """Sync WooCommerce orders"""
        # Check if WooCommerce API is available
        if not self.woo:
            messagebox.showerror("Error", 
                "WooCommerce API not connected!\n\n" +
                "Please make sure you're connected to WooCommerce first.")
            return
        
        self.log("Syncing WooCommerce orders...")
        
        try:
            # Get all orders first
            all_orders = self.woo.get_all_orders()
            
            # Filter for processing orders
            orders = [o for o in all_orders if o['status'] == 'processing']
            
            # Clear tree
            for item in self.orders_tree.get_children():
                self.orders_tree.delete(item)
            
            for order in orders:
                billing = order.get('billing', {})
                
                # Check if voucher already exists
                existing = self.acs_db.get_all_shipments({
                    'woocommerce_order_id': order['id']
                })
                
                # Determine if COD
                payment_method = order.get('payment_method', '')
                is_cod = payment_method == 'cod'
                
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
            
            self.log(f"✅ Synced {len(orders)} orders from WooCommerce")
            messagebox.showinfo("Success", f"Loaded {len(orders)} processing orders")
            
        except Exception as e:
            self.log(f"✗ Error syncing orders: {e}")
            messagebox.showerror("Error", f"Failed to sync orders:\n\n{e}")
    
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
        """Create ACS vouchers from selected orders"""
        selected = []
        
        for item in self.orders_tree.get_children():
            if self.orders_tree.item(item, 'text') == '☑':
                selected.append(item)
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select orders to create vouchers")
            return
        
        # Confirm
        if not messagebox.askyesno("Confirm", 
                                   f"Create {len(selected)} ACS vouchers?"):
            return
        
        self.log(f"Creating {len(selected)} vouchers...")
        
        success_count = 0
        errors = []
        
        for item in selected:
            values = self.orders_tree.item(item, 'values')
            order_id = values[1]
            
            # Get full order details
            try:
                all_orders = self.woo.get_all_orders()
                order = next((o for o in all_orders if str(o['id']) == str(order_id)), None)
                
                if order:
                    result = self.create_voucher_from_order(order)
                    if result:
                        success_count += 1
                        self.orders_tree.item(item, values=(*values[:-1], "✅ Created"))
                    else:
                        errors.append(f"Order #{order_id}: Failed to create voucher")
                else:
                    errors.append(f"Order #{order_id}: Not found")
                    
            except Exception as e:
                errors.append(f"Order #{order_id}: {str(e)}")
        
        # Show summary
        summary = f"Created {success_count}/{len(selected)} vouchers"
        if errors:
            summary += f"\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                summary += f"\n... and {len(errors)-5} more"
        
        self.log(summary)
        messagebox.showinfo("Complete", summary)
        
        self.refresh_stats()
        self.load_all_shipments()
    
    def create_voucher_from_order(self, order: Dict) -> bool:
        """Create voucher from WooCommerce order"""
        try:
            billing = order['billing']
            
            # Split address - CRITICAL!
            street, number = split_address(billing['address_1'])
            
            # Prepare shipment data with CORRECT field names
            shipment_data = {
                'recipient_name': f"{billing['first_name']} {billing['last_name']}",
                'recipient_address': street,  # Street ONLY!
                'recipient_address_number': number or '',  # Number separate!
                'recipient_region': billing['city'],  # REGION not CITY!
                'recipient_zipcode': billing['postcode'],
                'recipient_phone': format_phone(billing.get('phone', '')),
                'recipient_cell_phone': format_phone(billing.get('phone', '')),
                'weight': 1.0,  # Default weight
                'cod_amount': float(order['total']) if order['payment_method'] == 'cod' else 0,
                'reference1': f"Order #{order['id']}",
                'delivery_notes': f"WooCommerce Order #{order['id']}"
            }
            
            # Create voucher via ACS API
            result = self.acs_api.create_voucher(shipment_data)
            
            if result['success']:
                # Save to database
                self.acs_db.add_shipment({
                    'voucher_no': result['voucher_no'],
                    'source': 'ESHOP',
                    'woocommerce_order_id': order['id'],
                    'recipient_email': billing.get('email'),
                    'recipient_city': billing['city'],  # For display only
                    'status': 'READY',
                    **shipment_data
                })
                
                self.log(f"✅ Created voucher {result['voucher_no']} for order #{order['id']}")
                return True
            else:
                self.log(f"✗ Failed to create voucher for order #{order['id']}: {result['error']}")
                return False
                
        except Exception as e:
            self.log(f"✗ Error creating voucher: {e}")
            return False
    
    def create_manual_entry_tab(self):
        """Create manual entry tab"""
        
        # Instructions
        ttk.Label(self.manual_entry_frame, 
                 text="Manual Shipment Entry (for phone orders)", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Form frame
        form_frame = ttk.LabelFrame(self.manual_entry_frame, 
                                   text="Shipment Details", padding="20")
        form_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Entry fields with CORRECT structure
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
        
        for i, (label, field) in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, 
                                                   sticky='w', pady=5, padx=5)
            
            if field == 'notes':
                entry = tk.Text(form_frame, height=3, width=50)
            else:
                entry = ttk.Entry(form_frame, width=50)
            
            entry.grid(row=i, column=1, pady=5, padx=5)
            self.manual_fields[field] = entry
        
        # Buttons
        button_frame = ttk.Frame(self.manual_entry_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Save as Draft", 
                  command=lambda: self.save_manual_entry(create_voucher=False)).pack(
                      side='left', padx=5)
        ttk.Button(button_frame, text="Create Voucher Now", 
                  command=lambda: self.save_manual_entry(create_voucher=True)).pack(
                      side='left', padx=5)
        ttk.Button(button_frame, text="Clear Form", 
                  command=self.clear_manual_form).pack(side='left', padx=5)
    
    def save_manual_entry(self, create_voucher: bool = False):
        """Save manual entry with CORRECT validation and field mapping"""
        # Get values
        data = {}
        for field, widget in self.manual_fields.items():
            if isinstance(widget, tk.Text):
                data[field] = widget.get('1.0', 'end-1c').strip()
            else:
                data[field] = widget.get().strip()
        
        # Validate required fields
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
        
        # Validate zipcode
        if not validate_zipcode(data['recipient_zipcode']):
            messagebox.showerror("Invalid Zipcode", 
                "Zipcode must be exactly 5 digits")
            return
        
        # Validate phone
        phone = format_phone(data['recipient_phone'])
        if len(phone) != 10:
            messagebox.showerror("Invalid Phone", 
                "Phone must be exactly 10 digits")
            return
        
        # Format phone numbers
        data['recipient_phone'] = phone
        data['recipient_cell_phone'] = phone  # Use same for cell
        
        # Convert numeric fields
        try:
            data['weight'] = float(data.get('weight') or 1.0)
            data['cod_amount'] = float(data.get('cod_amount') or 0)
        except ValueError:
            messagebox.showerror("Invalid Number", 
                "Weight and COD amount must be valid numbers")
            return
        
        if create_voucher:
            # Create voucher immediately
            self.log("📝 Creating manual voucher...")
            
            # Prepare data for ACS API (needs recipient_region)
            api_data = {
                'recipient_name': data['recipient_name'],
                'recipient_address': data['recipient_address'],
                'recipient_address_number': data.get('recipient_address_number', ''),
                'recipient_region': data['recipient_region'],  # For ACS API
                'recipient_zipcode': data['recipient_zipcode'],
                'recipient_phone': data['recipient_phone'],
                'recipient_cell_phone': data['recipient_cell_phone'],
                'recipient_email': data.get('recipient_email', ''),
                'weight': data['weight'],
                'cod_amount': data['cod_amount'],
                'reference1': data.get('notes', ''),
                'delivery_notes': data.get('notes', '')
            }
            
            result = self.acs_api.create_voucher(api_data)
            
            if result['success']:
                # Prepare data for database (needs recipient_city)
                db_data = {
                    'voucher_no': result['voucher_no'],
                    'source': 'MANUAL',
                    'woocommerce_order_id': None,
                    'manual_reference': data.get('notes', ''),
                    'recipient_name': data['recipient_name'],
                    'recipient_address': data['recipient_address'],
                    'recipient_city': data['recipient_region'],  # For database display
                    'recipient_zipcode': data['recipient_zipcode'],
                    'recipient_phone': data['recipient_phone'],
                    'recipient_email': data.get('recipient_email', ''),
                    'weight': data['weight'],
                    'pieces': 1,
                    'cod_amount': data['cod_amount'],
                    'notes': data.get('notes', ''),
                    'status': 'READY'
                }
                
                # Save to database
                shipment_id = self.acs_db.add_shipment(db_data)
                
                if shipment_id:
                    self.log(f"✅ Created voucher {result['voucher_no']} and saved to database (ID: {shipment_id})")
                    messagebox.showinfo("Success", 
                                       f"✅ Voucher created successfully!\n\n" +
                                       f"Voucher Number: {result['voucher_no']}\n\n" +
                                       f"You can now export the PDF from the 'All Shipments' tab.")
                    
                    self.clear_manual_form()
                    self.refresh_stats()
                    self.load_all_shipments()
                else:
                    self.log(f"⚠️ Voucher {result['voucher_no']} created but failed to save to database")
                    messagebox.showwarning("Partial Success", 
                                          f"Voucher created: {result['voucher_no']}\n\n" +
                                          f"But failed to save to database.\n" +
                                          f"The voucher exists in ACS but not in local database.")
            else:
                error_msg = result.get('error', 'Unknown error')
                self.log(f"✗ Failed: {error_msg}")
                messagebox.showerror("Error", f"Failed to create voucher:\n\n{error_msg}")
        else:
            # Save as draft (no voucher created yet)
            db_data = {
                'voucher_no': None,
                'source': 'MANUAL',
                'woocommerce_order_id': None,
                'manual_reference': data.get('notes', ''),
                'recipient_name': data['recipient_name'],
                'recipient_address': data['recipient_address'],
                'recipient_city': data['recipient_region'],  # For database display
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
            
            self.log("✅ Saved manual entry as draft")
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
    
    def create_pickup_tab(self):
        """Create pickup management tab"""
        
        # Controls
        control_frame = ttk.Frame(self.pickup_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="Pickup Management & Tracking", 
                 font=('Arial', 12, 'bold')).pack(side='left')
        
        ttk.Button(control_frame, text="📋 Create Pickup List", 
                  command=self.create_pickup_list).pack(side='right', padx=5)
        ttk.Button(control_frame, text="📄 Export Pickup List PDF", 
                  command=self.export_pickup_list_pdf).pack(side='right', padx=5)
        ttk.Button(control_frame, text="🔄 Update Tracking", 
                  command=self.update_all_tracking).pack(side='right', padx=5)
        
        # Pickup info
        info_frame = ttk.LabelFrame(self.pickup_frame, 
                                   text="Pickup Information", padding="10")
        info_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(info_frame, text="Daily Pickup Time: 10:00", 
                 font=('Arial', 10, 'bold')).pack(anchor='w')
        ttk.Label(info_frame, text="Reminder: 15 minutes before (09:45)").pack(anchor='w')
        
        self.pickup_list_label = ttk.Label(info_frame, text="No pickup list created today", 
                                          foreground='red')
        self.pickup_list_label.pack(anchor='w', pady=5)
        
        # Instructions
        instructions = ttk.LabelFrame(self.pickup_frame, text="⚠️ IMPORTANT", padding="10")
        instructions.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(instructions, text="Pickup List is MANDATORY:", 
                 font=('Arial', 10, 'bold')).pack(anchor='w')
        ttk.Label(instructions, 
                 text="• Without creating the pickup list, voucher barcodes won't work!").pack(anchor='w')
        ttk.Label(instructions, 
                 text="• Create pickup list BEFORE courier arrives (10:00)").pack(anchor='w')
        ttk.Label(instructions, 
                 text="• Print the pickup list PDF and give it to the courier").pack(anchor='w')
    
    def create_pickup_list(self):
        """Create pickup list for today"""
        # Check if any vouchers exist for today
        stats = self.acs_db.get_today_stats()
        
        if stats['total'] == 0:
            messagebox.showwarning("No Shipments", 
                "No shipments found for today.\n\n" +
                "Create vouchers first before making a pickup list.")
            return
        
        if not messagebox.askyesno("Confirm", 
                                   f"Create pickup list for today's {stats['total']} shipments?\n\n" +
                                   f"E-Shop: {stats['eshop']}\n" +
                                   f"Manual: {stats['manual']}"):
            return
        
        self.log("📋 Creating pickup list...")
        
        # Create via API
        result = self.acs_api.create_pickup_list()
        
        if result['success']:
            pickup_list_no = result['pickup_list_no']
            self.current_pickup_list_no = pickup_list_no
            
            # Update database
            list_id, _ = self.acs_db.create_pickup_list()
            
            self.log(f"✅ Pickup list created: {pickup_list_no}")
            self.pickup_list_label.config(
                text=f"✅ Today's pickup list: {pickup_list_no}",
                foreground='green'
            )
            
            messagebox.showinfo("Success", 
                               f"✅ Pickup list created successfully!\n\n" +
                               f"Pickup List Number: {pickup_list_no}\n\n" +
                               f"Next: Export the PDF and print it for the courier.")
            
            self.refresh_stats()
        else:
            error_msg = result.get('error', 'Unknown error')
            
            # Check for unprinted vouchers
            if 'unprinted' in error_msg.lower():
                unprinted = result.get('unprinted_vouchers', [])
                if unprinted:
                    error_msg += f"\n\nUnprinted vouchers:\n" + "\n".join(unprinted[:5])
            
            self.log(f"✗ Failed to create pickup list: {error_msg}")
            messagebox.showerror("Error", f"Failed to create pickup list:\n\n{error_msg}")
    
    def export_pickup_list_pdf(self):
        """Export pickup list as PDF with CORRECT parameters"""
        if not self.current_pickup_list_no:
            messagebox.showwarning("No Pickup List", 
                "No pickup list has been created yet.\n\n" +
                "Create a pickup list first.")
            return
        
        # Ask where to save
        default_filename = f"pickup_list_{self.current_pickup_list_no}_{date.today().strftime('%Y%m%d')}.pdf"
        
        filename = filedialog.asksaveasfilename(
            title="Save Pickup List PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=default_filename
        )
        
        if not filename:
            return  # User cancelled
        
        self.log(f"📄 Exporting pickup list {self.current_pickup_list_no} to PDF...")
        
        # Export PDF with CORRECT parameters!
        result = self.acs_api.print_pickup_list(
            mass_number=self.current_pickup_list_no,
            pickup_date=date.today().strftime('%Y-%m-%d'),
            output_path=filename
        )
        
        if result['success']:
            self.log(f"✅ Pickup list PDF saved: {filename}")
            
            # Ask if user wants to open it
            if messagebox.askyesno("Success", 
                f"✅ Pickup list PDF saved!\n\n{filename}\n\nOpen the file now?"):
                try:
                    import os
                    os.startfile(filename)  # Windows
                except:
                    try:
                        import subprocess
                        subprocess.call(['xdg-open', filename])  # Linux
                    except:
                        pass
        else:
            error_msg = result.get('error', 'Unknown error')
            self.log(f"✗ Failed to export pickup list: {error_msg}")
            messagebox.showerror("Export Failed", 
                f"Failed to export pickup list PDF:\n\n{error_msg}")
    
    def update_all_tracking(self):
        """Update tracking for all in-transit shipments"""
        self.log("🔄 Updating tracking information...")
        
        shipments = self.acs_db.get_all_shipments({'status': 'PICKED_UP'})
        
        if not shipments:
            messagebox.showinfo("No Shipments", "No shipments are currently in transit")
            return
        
        updated = 0
        for ship in shipments:
            if ship['voucher_no']:
                result = self.acs_api.track_shipment_summary(ship['voucher_no'])
                if result['success']:
                    # Update status
                    self.acs_db.update_shipment(ship['id'], {
                        'tracking_data': str(result),
                        'status': 'IN_TRANSIT'
                    })
                    updated += 1
        
        self.log(f"✅ Updated tracking for {updated} shipments")
        messagebox.showinfo("Complete", f"Updated tracking for {updated} shipments")
        self.load_all_shipments()
    
    def show_shipment_details(self, event):
        """Show detailed shipment info"""
        selection = self.shipments_tree.selection()
        if not selection:
            return
        
        item = self.shipments_tree.item(selection[0])
        ship_id = item['values'][0]
        
        shipment = self.acs_db.get_shipment(shipment_id=ship_id)
        
        if shipment:
            details = f"SHIPMENT DETAILS\n"
            details += f"{'='*50}\n\n"
            details += f"Shipment ID: {shipment['id']}\n"
            details += f"Voucher: {shipment['voucher_no'] or 'Not created'}\n"
            details += f"Source: {shipment['source']}\n"
            details += f"Status: {shipment['status']}\n"
            details += f"\nRecipient:\n"
            details += f"  {shipment['recipient_name']}\n"
            details += f"  {shipment['recipient_address']} {shipment.get('recipient_address_number', '')}\n"
            details += f"  {shipment['recipient_zipcode']} {shipment['recipient_city']}\n"
            details += f"  Phone: {shipment['recipient_phone']}\n"
            
            if shipment.get('recipient_email'):
                details += f"  Email: {shipment['recipient_email']}\n"
            
            details += f"\nShipment Details:\n"
            details += f"  Weight: {shipment['weight']}kg\n"
            details += f"  Pieces: {shipment['pieces']}\n"
            details += f"  COD: €{shipment['cod_amount']}\n"
            
            if shipment.get('manual_reference'):
                details += f"\nNotes: {shipment['manual_reference']}\n"
            
            if shipment.get('pickup_list_no'):
                details += f"\nPickup List: {shipment['pickup_list_no']}\n"
            
            messagebox.showinfo(f"Shipment #{ship_id}", details)
    
    def export_shipments(self):
        """Export shipments to Excel/CSV"""
        import csv
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"shipments_{date.today().strftime('%Y%m%d')}.csv"
        )
        
        if filename:
            shipments = self.acs_db.get_all_shipments()
            
            if shipments:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=shipments[0].keys())
                    writer.writeheader()
                    writer.writerows(shipments)
                
                self.log(f"📊 Exported {len(shipments)} shipments to {filename}")
                messagebox.showinfo("Success", f"Exported to {filename}")
            else:
                messagebox.showinfo("No Data", "No shipments to export")
    
    def start_reminder_thread(self):
        """Start background thread for pickup reminders"""
        def check_reminders():
            import time
            while True:
                now = datetime.now()
                pickup_datetime = datetime.combine(date.today(), self.pickup_time)
                reminder_datetime = pickup_datetime - timedelta(minutes=self.reminder_minutes)
                
                if (reminder_datetime <= now < pickup_datetime and 
                    not self.reminder_active):
                    self.show_pickup_reminder()
                    self.reminder_active = True
                elif now >= pickup_datetime:
                    self.reminder_active = False
                
                time.sleep(60)  # Check every minute
        
        thread = threading.Thread(target=check_reminders, daemon=True)
        thread.start()
    
    def show_pickup_reminder(self):
        """Show pickup reminder popup"""
        stats = self.acs_db.get_today_stats()
        
        if stats['total'] == 0:
            return
        
        reminder = tk.Toplevel(self.master)
        reminder.title("🔔 ACS Pickup Reminder")
        reminder.geometry("400x250")
        reminder.grab_set()
        
        frame = ttk.Frame(reminder, padding="20")
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text="🔔 COURIER PICKUP REMINDER", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        ttk.Label(frame, text=f"Pickup time: {self.pickup_time.strftime('%H:%M')}", 
                 font=('Arial', 11)).pack(pady=5)
        
        ttk.Label(frame, text=f"Total shipments: {stats['total']}", 
                 font=('Arial', 11)).pack(pady=5)
        ttk.Label(frame, text=f"E-Shop: {stats['eshop']} | Manual: {stats['manual']}", 
                 font=('Arial', 10)).pack(pady=5)
        
        if not self.current_pickup_list_no:
            ttk.Label(frame, text="⚠️ PICKUP LIST NOT CREATED YET!", 
                     font=('Arial', 11, 'bold'), foreground='red').pack(pady=10)
        
        ttk.Button(frame, text="✅ Ready", 
                  command=reminder.destroy).pack(pady=10)
        
        # Play system sound
        reminder.bell()
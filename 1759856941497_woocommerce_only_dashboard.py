import tkinter as tk
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime, timedelta
from typing import Dict, List
import threading
from collections import defaultdict
import csv
from acs_integration import ACSShippingTab

class WooCommerceAPI:
    """WooCommerce REST API handler with pagination support"""
    
    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str):
        self.store_url = store_url.rstrip('/')
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            url = f"{self.store_url}/wp-json/wc/v3/system_status"
            response = requests.get(url, auth=self.auth, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_all_products(self, progress_callback=None) -> List[Dict]:
        """Get ALL products with pagination"""
        all_products = []
        page = 1
        per_page = 100
        
        while True:
            try:
                url = f"{self.store_url}/wp-json/wc/v3/products"
                params = {'per_page': per_page, 'page': page}
                
                response = requests.get(url, auth=self.auth, params=params, timeout=30)
                response.raise_for_status()
                
                products = response.json()
                
                if not products:
                    break
                    
                all_products.extend(products)
                
                if progress_callback:
                    progress_callback(len(all_products))
                
                # Check if there are more pages
                total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                    
                page += 1
                
            except Exception as e:
                print(f"Error fetching products page {page}: {e}")
                break
        
        return all_products
    
    def get_all_orders(self, progress_callback=None) -> List[Dict]:
        """Get ALL orders with pagination"""
        all_orders = []
        page = 1
        per_page = 100
        
        while True:
            try:
                url = f"{self.store_url}/wp-json/wc/v3/orders"
                params = {'per_page': per_page, 'page': page, 'status': 'any'}
                
                response = requests.get(url, auth=self.auth, params=params, timeout=30)
                response.raise_for_status()
                
                orders = response.json()
                
                if not orders:
                    break
                    
                all_orders.extend(orders)
                
                if progress_callback:
                    progress_callback(len(all_orders))
                
                # Check if there are more pages
                total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                    
                page += 1
                
            except Exception as e:
                print(f"Error fetching orders page {page}: {e}")
                break
        
        return all_orders
    
    def get_order_meta(self, order_id: int) -> Dict:
        """Get order metadata including VAT number"""
        try:
            url = f"{self.store_url}/wp-json/wc/v3/orders/{order_id}"
            response = requests.get(url, auth=self.auth, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching order meta: {e}")
            return {}

class EnhancedWooCommerceDashboard:
    """Enhanced WooCommerce Dashboard with advanced analytics"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Roussakis E-shop Analytics Dashboard - Enhanced")
        self.root.geometry("1800x1000")
        
        # ===== AUTO-CONNECT CONFIGURATION =====
        # Your WooCommerce credentials (change if needed)
        self.STORE_URL = "https://roussakis.com.gr"
        self.CONSUMER_KEY = "ck_bb11ea8930c80ab895887236e037ddcfbee003e1"
        self.CONSUMER_SECRET = "cs_c7cc521fbe93def7c731a920632c0c23c50d0bd7"
        
        self.woo = None
        self.all_products = []
        self.all_orders = []
        self.customer_data = {}
        self.refresh_interval = 900  # 15 minutes in seconds
        self.refresh_timer = None
        self.seconds_until_refresh = self.refresh_interval
        
        # Setup GUI first (but ACS tab will be placeholder)
        self.setup_gui()
        
        # THEN auto-connect
        self.auto_connect()
        
    def setup_gui(self):
        """Setup main interface"""
        # Top banner
        banner_frame = tk.Frame(self.root, bg='#2C3E50', height=50)
        banner_frame.pack(fill='x')
        tk.Label(banner_frame, text="🚀 ROUSSAKIS E-SHOP - ADVANCED ANALYTICS DASHBOARD", 
                bg='#2C3E50', fg='white', font=('Arial', 14, 'bold')).pack(pady=12)
        
        # Create notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Products with Search
        self.products_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.products_frame, text="📦 Products")
        self.setup_products_tab()
        
        # Tab 2: Orders with Details
        self.orders_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.orders_frame, text="🛒 Orders")
        self.setup_orders_tab()
        
        # Tab 3: Customer Analytics
        self.customers_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.customers_frame, text="👥 Customers")
        self.setup_customers_tab()
        
        # Tab 4: Product Performance
        self.performance_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.performance_frame, text="📊 Product Stats")
        self.setup_performance_tab()
        
        # Tab 5: Sales Analytics
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="💰 Sales Analytics")
        self.setup_analytics_tab()
        
        # Tab 6: Log (MUST BE BEFORE ACS!)
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="📝 Activity Log")
        self.setup_log_tab()

        # Tab 7: ACS Shipping - PLACEHOLDER (will be created after connection)
        self.acs_placeholder_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.acs_placeholder_frame, text="📦 ACS Shipping")
        ttk.Label(self.acs_placeholder_frame, 
                 text="⏳ Connecting to WooCommerce...\n\nACS Shipping will load once connected.",
                 font=('Arial', 14)).pack(expand=True)
        
        # Status bar with auto-refresh countdown
        self.setup_status_bar()
    
    def auto_connect(self):
        """Auto-connect to WooCommerce on startup"""
        self.log("🔄 Auto-connecting to WooCommerce...")
        self.status_var.set("⏳ Connecting to WooCommerce...")
        
        def connect_thread():
            try:
                # Create WooCommerce API instance
                self.woo = WooCommerceAPI(self.STORE_URL, self.CONSUMER_KEY, self.CONSUMER_SECRET)
                
                # Test connection
                if self.woo.test_connection():
                    self.root.after(0, self.on_connection_success)
                else:
                    self.root.after(0, self.on_connection_failed)
                    
            except Exception as e:
                self.root.after(0, lambda: self.on_connection_error(str(e)))
        
        # Connect in background thread
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()
    
    def on_connection_success(self):
        """Called when WooCommerce connection succeeds"""
        self.status_var.set("✅ Connected to WooCommerce")
        self.log("✅ SUCCESS! Connected to WooCommerce API")
        
        # NOW create the ACS tab with working WooCommerce API
        self.create_acs_tab()
        
        # Load all data
        self.load_all_data()
        
        # Start auto-refresh timer
        self.start_refresh_countdown()
        
        messagebox.showinfo("Connected", 
            "✅ Connected successfully to WooCommerce!\n\n" +
            "Loading all data...\n" +
            "Auto-refresh: Every 15 minutes")
    
    def on_connection_failed(self):
        """Called when WooCommerce connection fails"""
        self.status_var.set("❌ Connection Failed")
        self.log("❌ ERROR: Failed to connect to WooCommerce")
        
        messagebox.showerror("Connection Failed", 
            "Could not connect to WooCommerce API.\n\n" +
            "Please check:\n" +
            "- Store URL is correct\n" +
            "- API keys are correct\n" +
            "- Internet connection\n\n" +
            "The app will retry in background...")
        
        # Retry after 30 seconds
        self.root.after(30000, self.auto_connect)
    
    def on_connection_error(self, error_msg):
        """Called when connection throws an exception"""
        self.status_var.set("❌ Connection Error")
        self.log(f"❌ ERROR: {error_msg}")
        
        messagebox.showerror("Error", f"Connection error:\n\n{error_msg}")
        
        # Retry after 30 seconds
        self.root.after(30000, self.auto_connect)
    
    def create_acs_tab(self):
        """Create ACS tab after WooCommerce is connected"""
        try:
            # Remove placeholder
            self.notebook.forget(self.acs_placeholder_frame)
            
            # Create real ACS tab with working WooCommerce API
            self.acs_frame = ACSShippingTab(self.notebook, self.woo, self.log)
            self.notebook.add(self.acs_frame, text="📦 ACS Shipping")
            
            self.log("✅ ACS Shipping module initialized")
            
        except Exception as e:
            self.log(f"❌ Error creating ACS tab: {e}")
            messagebox.showerror("Error", f"Failed to initialize ACS module:\n\n{e}")
        
    def setup_products_tab(self):
        """Setup products tab with search and filters"""
        # Control frame
        control_frame = ttk.Frame(self.products_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="Products", 
                 font=('Arial', 14, 'bold')).grid(row=0, column=0, sticky='w')
        
        # Search box
        ttk.Label(control_frame, text="Search:").grid(row=1, column=0, sticky='w', pady=5)
        self.product_search_var = tk.StringVar()
        self.product_search_var.trace('w', lambda *args: self.filter_products())
        search_entry = ttk.Entry(control_frame, textvariable=self.product_search_var, width=40)
        search_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # Stock filter
        ttk.Label(control_frame, text="Stock:").grid(row=1, column=2, padx=(20,5))
        self.stock_filter_var = tk.StringVar(value="All")
        stock_combo = ttk.Combobox(control_frame, textvariable=self.stock_filter_var,
                                    values=["All", "In Stock", "Out of Stock"], 
                                    state="readonly", width=12)
        stock_combo.grid(row=1, column=3)
        stock_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_products())
        
        # Buttons
        ttk.Button(control_frame, text="🔄 Refresh", 
                  command=self.load_all_data).grid(row=1, column=4, padx=5)
        ttk.Button(control_frame, text="📊 Export CSV", 
                  command=self.export_products).grid(row=1, column=5, padx=5)
        
        # Products count
        self.products_count_label = ttk.Label(control_frame, text="Products: 0")
        self.products_count_label.grid(row=1, column=6, padx=20)
        
        # Products tree
        tree_frame = ttk.Frame(self.products_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0,10))
        
        columns = ('ID', 'SKU', 'Name', 'Price', 'Stock Qty', 'Stock Status')
        self.products_tree = ttk.Treeview(tree_frame, columns=columns, 
                                         show='headings', height=35)
        
        for col in columns:
            self.products_tree.heading(col, text=col)
        
        self.products_tree.column('ID', width=70)
        self.products_tree.column('SKU', width=150)
        self.products_tree.column('Name', width=600)
        self.products_tree.column('Price', width=100, anchor='e')
        self.products_tree.column('Stock Qty', width=100, anchor='center')
        self.products_tree.column('Stock Status', width=120)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', 
                                 command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=scrollbar.set)
        
        self.products_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
    def setup_orders_tab(self):
        """Setup orders tab with all details"""
        control_frame = ttk.Frame(self.orders_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="Orders", 
                 font=('Arial', 14, 'bold')).grid(row=0, column=0, sticky='w')
        
        # Search
        ttk.Label(control_frame, text="Search:").grid(row=1, column=0, sticky='w', pady=5)
        self.order_search_var = tk.StringVar()
        self.order_search_var.trace('w', lambda *args: self.filter_orders())
        ttk.Entry(control_frame, textvariable=self.order_search_var, width=40).grid(row=1, column=1, padx=5)
        
        # Status filter
        ttk.Label(control_frame, text="Status:").grid(row=1, column=2, padx=(20,5))
        self.status_filter_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(control_frame, textvariable=self.status_filter_var,
                                    values=["All", "completed", "processing", "pending", "on-hold"], 
                                    state="readonly", width=12)
        status_combo.grid(row=1, column=3)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_orders())
        
        ttk.Button(control_frame, text="📊 Export CSV", 
                  command=self.export_orders).grid(row=1, column=4, padx=5)
        
        self.orders_count_label = ttk.Label(control_frame, text="Orders: 0")
        self.orders_count_label.grid(row=1, column=5, padx=20)
        
        # Orders tree
        tree_frame = ttk.Frame(self.orders_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0,10))
        
        columns = ('Order ID', 'Date', 'Customer', 'Email', 'Phone', 'Payment', 'Shipping', 'Total', 'Status')
        self.orders_tree = ttk.Treeview(tree_frame, columns=columns, 
                                       show='headings', height=35)
        
        for col in columns:
            self.orders_tree.heading(col, text=col)
        
        self.orders_tree.column('Order ID', width=80)
        self.orders_tree.column('Date', width=100)
        self.orders_tree.column('Customer', width=180)
        self.orders_tree.column('Email', width=220)
        self.orders_tree.column('Phone', width=120)
        self.orders_tree.column('Payment', width=120)
        self.orders_tree.column('Shipping', width=150)
        self.orders_tree.column('Total', width=100, anchor='e')
        self.orders_tree.column('Status', width=100)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', 
                                 command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=scrollbar.set)
        
        self.orders_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.orders_tree.bind('<Double-Button-1>', self.show_order_details)
        
    def setup_customers_tab(self):
        """Setup customer analytics tab"""
        control_frame = ttk.Frame(self.customers_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="Customer Intelligence", 
                 font=('Arial', 14, 'bold')).pack(side='left')
        
        ttk.Button(control_frame, text="📊 Export CSV", 
                  command=self.export_customers).pack(side='right', padx=5)
        
        # Customers tree
        tree_frame = ttk.Frame(self.customers_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0,10))
        
        columns = ('Customer', 'Email', 'Phone', 'Orders', 'Total Spent', 'Avg Order', 'Type', 'Last Order')
        self.customers_tree = ttk.Treeview(tree_frame, columns=columns, 
                                          show='headings', height=35)
        
        for col in columns:
            self.customers_tree.heading(col, text=col, 
                                       command=lambda c=col: self.sort_customers(c))
        
        self.customers_tree.column('Customer', width=200)
        self.customers_tree.column('Email', width=230)
        self.customers_tree.column('Phone', width=120)
        self.customers_tree.column('Orders', width=80, anchor='center')
        self.customers_tree.column('Total Spent', width=120, anchor='e')
        self.customers_tree.column('Avg Order', width=100, anchor='e')
        self.customers_tree.column('Type', width=100)
        self.customers_tree.column('Last Order', width=100)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', 
                                 command=self.customers_tree.yview)
        self.customers_tree.configure(yscrollcommand=scrollbar.set)
        
        self.customers_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
    def setup_performance_tab(self):
        """Setup product performance tab"""
        control_frame = ttk.Frame(self.performance_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="Product Performance Statistics", 
                 font=('Arial', 14, 'bold')).pack(side='left')
        
        ttk.Button(control_frame, text="📊 Export CSV", 
                  command=self.export_performance).pack(side='right', padx=5)
        
        # Performance tree
        tree_frame = ttk.Frame(self.performance_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0,10))
        
        columns = ('Rank', 'SKU', 'Product Name', 'Times Sold', 'Total Qty', 'Revenue', 'Avg Price')
        self.performance_tree = ttk.Treeview(tree_frame, columns=columns, 
                                            show='headings', height=35)
        
        for col in columns:
            self.performance_tree.heading(col, text=col)
        
        self.performance_tree.column('Rank', width=60, anchor='center')
        self.performance_tree.column('SKU', width=150)
        self.performance_tree.column('Product Name', width=500)
        self.performance_tree.column('Times Sold', width=100, anchor='center')
        self.performance_tree.column('Total Qty', width=100, anchor='center')
        self.performance_tree.column('Revenue', width=120, anchor='e')
        self.performance_tree.column('Avg Price', width=100, anchor='e')
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', 
                                 command=self.performance_tree.yview)
        self.performance_tree.configure(yscrollcommand=scrollbar.set)
        
        self.performance_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
    def setup_analytics_tab(self):
        """Setup sales analytics tab"""
        main_frame = ttk.Frame(self.analytics_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(header_frame, text="Sales Analytics", 
                 font=('Arial', 16, 'bold')).pack(side='left')
        
        # Three columns for time periods
        columns_frame = ttk.Frame(main_frame)
        columns_frame.pack(fill='both', expand=True)
        
        # Last Day
        day_frame = ttk.LabelFrame(columns_frame, text="LAST 24 HOURS", padding="10")
        day_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        self.create_period_display(day_frame, 'day')
        
        # Last Week
        week_frame = ttk.LabelFrame(columns_frame, text="LAST 7 DAYS", padding="10")
        week_frame.pack(side='left', fill='both', expand=True, padx=5)
        self.create_period_display(week_frame, 'week')
        
        # Last Month
        month_frame = ttk.LabelFrame(columns_frame, text="LAST 30 DAYS", padding="10")
        month_frame.pack(side='left', fill='both', expand=True, padx=(5, 0))
        self.create_period_display(month_frame, 'month')
        
        # Payment & Shipping breakdown
        breakdown_frame = ttk.Frame(main_frame)
        breakdown_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        # Payment methods
        payment_frame = ttk.LabelFrame(breakdown_frame, text="PAYMENT METHODS", padding="10")
        payment_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        self.payment_text = scrolledtext.ScrolledText(payment_frame, height=10, width=40)
        self.payment_text.pack(fill='both', expand=True)
        
        # Shipping methods
        shipping_frame = ttk.LabelFrame(breakdown_frame, text="SHIPPING METHODS", padding="10")
        shipping_frame.pack(side='left', fill='both', expand=True, padx=(5, 0))
        
        self.shipping_text = scrolledtext.ScrolledText(shipping_frame, height=10, width=40)
        self.shipping_text.pack(fill='both', expand=True)
        
    def create_period_display(self, parent, period_key):
        """Create metrics display for a time period"""
        if not hasattr(self, 'period_widgets'):
            self.period_widgets = {}
        
        self.period_widgets[period_key] = {}
        
        # Orders
        ttk.Label(parent, text="Total Orders:", font=('Arial', 10, 'bold')).pack(anchor='w')
        orders_label = ttk.Label(parent, text="0", font=('Arial', 24, 'bold'), foreground='#2C3E50')
        orders_label.pack(anchor='w')
        self.period_widgets[period_key]['orders'] = orders_label
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        # Revenue
        ttk.Label(parent, text="Total Revenue:", font=('Arial', 10, 'bold')).pack(anchor='w')
        revenue_label = ttk.Label(parent, text="€0.00", font=('Arial', 20, 'bold'), foreground='#27AE60')
        revenue_label.pack(anchor='w')
        self.period_widgets[period_key]['revenue'] = revenue_label
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        # Average
        ttk.Label(parent, text="Avg Order:", font=('Arial', 10, 'bold')).pack(anchor='w')
        avg_label = ttk.Label(parent, text="€0.00", font=('Arial', 16), foreground='#3498DB')
        avg_label.pack(anchor='w')
        self.period_widgets[period_key]['avg'] = avg_label
        
    def setup_log_tab(self):
        """Setup log tab"""
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD)
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
    def setup_status_bar(self):
        """Setup status bar with auto-refresh countdown"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side='bottom', fill='x', padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="Starting...")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side='left')
        
        self.refresh_label = ttk.Label(status_frame, text="")
        self.refresh_label.pack(side='right')
        
    def log(self, message: str):
        """Add to activity log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
        
    def load_all_data(self):
        """Load all data in background thread"""
        def load():
            try:
                # Show loading status
                self.root.after(0, lambda: self.status_var.set("⏳ Loading data..."))
                
                # Load products
                self.root.after(0, lambda: self.log("📦 Loading ALL products..."))
                
                def product_progress(count):
                    self.root.after(0, lambda c=count: self.status_var.set(f"⏳ Loading products... {c}"))
                
                self.all_products = self.woo.get_all_products(product_progress)
                self.root.after(0, lambda: self.log(f"✅ Loaded {len(self.all_products)} products"))
                
                # Load orders
                self.root.after(0, lambda: self.log("🛒 Loading ALL orders..."))
                
                def order_progress(count):
                    self.root.after(0, lambda c=count: self.status_var.set(f"⏳ Loading orders... {c}"))
                
                self.all_orders = self.woo.get_all_orders(order_progress)
                self.root.after(0, lambda: self.log(f"✅ Loaded {len(self.all_orders)} orders"))
                
                # Process data
                self.root.after(0, lambda: self.log("🔄 Processing customer analytics..."))
                self.root.after(0, self.process_customer_data)
                
                self.root.after(0, lambda: self.log("🔄 Processing product performance..."))
                self.root.after(0, self.process_product_performance)
                
                # Update all displays
                self.root.after(0, self.display_products)
                self.root.after(0, self.display_orders)
                self.root.after(0, self.display_customers)
                self.root.after(0, self.display_performance)
                self.root.after(0, self.update_analytics)
                
                self.root.after(0, lambda: self.status_var.set("✅ All data loaded"))
                self.root.after(0, lambda: self.log("✅ All data loaded successfully!"))
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Error loading data: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load data:\n{e}"))
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
        
    def display_products(self):
        """Display products in tree"""
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        
        for product in self.all_products:
            self.products_tree.insert('', 'end', values=(
                product['id'],
                product.get('sku', 'N/A'),
                product['name'],
                f"€{product.get('regular_price', product.get('price', '0'))}",
                product.get('stock_quantity', 'N/A'),
                product.get('stock_status', 'N/A')
            ), tags=(product['id'],))
        
        self.products_count_label.config(text=f"Products: {len(self.all_products)}")
        self.filter_products()
        
    def filter_products(self):
        """Filter products based on search and filters"""
        search_term = self.product_search_var.get().lower()
        stock_filter = self.stock_filter_var.get()
        
        visible_count = 0
        for item in self.products_tree.get_children():
            values = self.products_tree.item(item)['values']
            
            # Search filter
            if search_term:
                if not any(search_term in str(v).lower() for v in values):
                    self.products_tree.detach(item)
                    continue
            
            # Stock filter
            if stock_filter != "All":
                stock_status = values[5]
                if stock_filter == "In Stock" and stock_status != "instock":
                    self.products_tree.detach(item)
                    continue
                elif stock_filter == "Out of Stock" and stock_status != "outofstock":
                    self.products_tree.detach(item)
                    continue
            
            self.products_tree.reattach(item, '', 'end')
            visible_count += 1
        
        self.products_count_label.config(text=f"Products: {visible_count} / {len(self.all_products)}")
        
    def display_orders(self):
        """Display orders with all details"""
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
        
        for order in self.all_orders:
            billing = order.get('billing', {})
            
            # Get payment method with card type
            payment_method = order.get('payment_method_title', 'N/A')
            
            # Try to extract card type from meta data or payment title
            card_type = None
            meta_data = order.get('meta_data', [])
            
            # Check meta data for card type
            for meta in meta_data:
                key = meta.get('key', '')
                value = meta.get('value', '')
                if key in ['_stripe_card_brand', '_card_type', '_wc_stripe_card_type', '_card_brand'] and value:
                    card_type = value
                    break
            
            # If not in meta, check payment method title
            if not card_type and payment_method:
                for brand in ['Visa', 'Mastercard', 'American Express', 'Amex', 'Discover', 'Diners', 'JCB']:
                    if brand.lower() in payment_method.lower():
                        card_type = brand
                        break
            
            # Format payment method with card type
            if card_type:
                payment_display = f"{payment_method} ({card_type})"
            else:
                payment_display = payment_method
            
            # Get shipping method
            shipping_lines = order.get('shipping_lines', [])
            shipping_method = shipping_lines[0]['method_title'] if shipping_lines else 'N/A'
            
            order_date = order['date_created'].split('T')[0]
            
            self.orders_tree.insert('', 'end', values=(
                order['id'],
                order_date,
                f"{billing.get('first_name', '')} {billing.get('last_name', '')}",
                billing.get('email', ''),
                billing.get('phone', ''),
                payment_display,
                shipping_method,
                f"€{order['total']}",
                order['status']
            ), tags=(order['id'],))
        
        self.orders_count_label.config(text=f"Orders: {len(self.all_orders)}")
        self.filter_orders()
        
    def filter_orders(self):
        """Filter orders based on search and status"""
        search_term = self.order_search_var.get().lower()
        status_filter = self.status_filter_var.get()
        
        visible_count = 0
        for item in self.orders_tree.get_children():
            values = self.orders_tree.item(item)['values']
            
            # Search filter
            if search_term:
                if not any(search_term in str(v).lower() for v in values):
                    self.orders_tree.detach(item)
                    continue
            
            # Status filter
            if status_filter != "All":
                if values[8] != status_filter:
                    self.orders_tree.detach(item)
                    continue
            
            self.orders_tree.reattach(item, '', 'end')
            visible_count += 1
        
        self.orders_count_label.config(text=f"Orders: {visible_count} / {len(self.all_orders)}")
        
    def process_customer_data(self):
        """Process customer analytics data"""
        self.customer_data = {}
        
        for order in self.all_orders:
            billing = order.get('billing', {})
            email = billing.get('email', 'unknown')
            
            if email not in self.customer_data:
                self.customer_data[email] = {
                    'name': f"{billing.get('first_name', '')} {billing.get('last_name', '')}",
                    'email': email,
                    'phone': billing.get('phone', ''),
                    'orders': [],
                    'total_spent': 0.0,
                    'order_count': 0
                }
            
            self.customer_data[email]['orders'].append(order)
            self.customer_data[email]['total_spent'] += float(order.get('total', 0))
            self.customer_data[email]['order_count'] += 1
        
    def display_customers(self):
        """Display customer analytics"""
        for item in self.customers_tree.get_children():
            self.customers_tree.delete(item)
        
        # Sort by total spent (descending)
        sorted_customers = sorted(self.customer_data.values(), 
                                 key=lambda x: x['total_spent'], reverse=True)
        
        for customer in sorted_customers:
            order_count = customer['order_count']
            total_spent = customer['total_spent']
            avg_order = total_spent / order_count if order_count > 0 else 0
            
            # Determine customer type
            if order_count == 1:
                customer_type = "🆕 NEW"
            elif order_count >= 10:
                customer_type = "⭐ VIP"
            else:
                customer_type = f"🔄 RETURNING"
            
            # Last order date
            last_order = max(customer['orders'], key=lambda x: x['date_created'])
            last_order_date = last_order['date_created'].split('T')[0]
            
            self.customers_tree.insert('', 'end', values=(
                customer['name'],
                customer['email'],
                customer['phone'],
                order_count,
                f"€{total_spent:,.2f}",
                f"€{avg_order:,.2f}",
                customer_type,
                last_order_date
            ))
        
    def sort_customers(self, col):
        """Sort customers by column"""
        # Simple sorting implementation
        items = [(self.customers_tree.set(item, col), item) 
                for item in self.customers_tree.get_children('')]
        
        # Try to sort numerically if possible
        try:
            items.sort(key=lambda t: float(t[0].replace('€', '').replace(',', '').split()[0]), 
                      reverse=True)
        except:
            items.sort(reverse=True)
        
        for index, (val, item) in enumerate(items):
            self.customers_tree.move(item, '', index)
        
    def process_product_performance(self):
        """Process product sales statistics"""
        self.product_stats = defaultdict(lambda: {
            'name': '',
            'sku': '',
            'times_sold': 0,
            'total_qty': 0,
            'total_revenue': 0.0
        })
        
        for order in self.all_orders:
            # Only count completed orders
            if order['status'] not in ['completed', 'processing']:
                continue
                
            for item in order.get('line_items', []):
                product_id = item['product_id']
                
                self.product_stats[product_id]['name'] = item['name']
                self.product_stats[product_id]['sku'] = item.get('sku', 'N/A')
                self.product_stats[product_id]['times_sold'] += 1
                self.product_stats[product_id]['total_qty'] += item['quantity']
                self.product_stats[product_id]['total_revenue'] += float(item['total'])
        
    def display_performance(self):
        """Display product performance statistics"""
        for item in self.performance_tree.get_children():
            self.performance_tree.delete(item)
        
        # Sort by revenue (descending)
        sorted_products = sorted(self.product_stats.items(), 
                                key=lambda x: x[1]['total_revenue'], reverse=True)
        
        for rank, (product_id, stats) in enumerate(sorted_products, 1):
            avg_price = stats['total_revenue'] / stats['total_qty'] if stats['total_qty'] > 0 else 0
            
            self.performance_tree.insert('', 'end', values=(
                rank,
                stats['sku'],
                stats['name'],
                stats['times_sold'],
                stats['total_qty'],
                f"€{stats['total_revenue']:,.2f}",
                f"€{avg_price:.2f}"
            ))
        
    def update_analytics(self):
        """Update sales analytics"""
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        day_orders = []
        week_orders = []
        month_orders = []
        payment_methods = defaultdict(int)
        shipping_methods = defaultdict(int)
        
        for order in self.all_orders:
            order_date = datetime.fromisoformat(order['date_created'].replace('Z', '+00:00'))
            
            if order_date >= day_ago:
                day_orders.append(order)
            if order_date >= week_ago:
                week_orders.append(order)
            if order_date >= month_ago:
                month_orders.append(order)
                
                # Count payment methods
                payment = order.get('payment_method_title', 'Unknown')
                payment_methods[payment] += 1
                
                # Count shipping methods
                shipping_lines = order.get('shipping_lines', [])
                if shipping_lines:
                    shipping = shipping_lines[0]['method_title']
                    shipping_methods[shipping] += 1
        
        self.update_metrics('day', day_orders)
        self.update_metrics('week', week_orders)
        self.update_metrics('month', month_orders)
        
        # Update payment methods
        self.payment_text.delete('1.0', 'end')
        for method, count in sorted(payment_methods.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(month_orders) * 100) if month_orders else 0
            self.payment_text.insert('end', f"{method}: {count} ({percentage:.1f}%)\n")
        
        # Update shipping methods
        self.shipping_text.delete('1.0', 'end')
        for method, count in sorted(shipping_methods.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(month_orders) * 100) if month_orders else 0
            self.shipping_text.insert('end', f"{method}: {count} ({percentage:.1f}%)\n")
        
    def update_metrics(self, period_key, orders):
        """Update metrics for a time period"""
        widgets = self.period_widgets.get(period_key, {})
        
        total_orders = len(orders)
        total_revenue = sum(float(order.get('total', 0)) for order in orders)
        avg_order = total_revenue / total_orders if total_orders > 0 else 0
        
        widgets['orders'].config(text=str(total_orders))
        widgets['revenue'].config(text=f"€{total_revenue:,.2f}")
        widgets['avg'].config(text=f"€{avg_order:,.2f}")
        
    def show_order_details(self, event):
        """Show detailed order information in popup"""
        selection = self.orders_tree.selection()
        if not selection:
            return
        
        order_id = self.orders_tree.item(selection[0])['values'][0]
        order = next((o for o in self.all_orders if o['id'] == order_id), None)
        
        if not order:
            return
        
        popup = tk.Toplevel(self.root)
        popup.title(f"Order #{order_id} - Full Details")
        popup.geometry("700x800")
        
        text = scrolledtext.ScrolledText(popup, wrap=tk.WORD, width=80, height=45)
        text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Get VAT number and card type from meta data
        meta_data = order.get('meta_data', [])
        vat_number = None
        card_type = None
        card_last4 = None
        
        # Common meta keys for card information
        card_type_keys = ['_stripe_card_brand', '_card_type', '_payment_method_title', 
                         '_wc_stripe_card_type', '_card_brand']
        card_last4_keys = ['_stripe_card_last4', '_card_last4', '_last4']
        
        for meta in meta_data:
            key = meta.get('key', '')
            value = meta.get('value', '')
            
            # VAT Number
            if key == '_billing_vat_number':
                vat_number = value
            
            # Card Type/Brand
            if key in card_type_keys and value:
                card_type = value
            
            # Last 4 digits
            if key in card_last4_keys and value:
                card_last4 = value
        
        billing = order['billing']
        shipping = order['shipping']
        
        order_date = datetime.fromisoformat(order['date_created'].replace('Z', '+00:00'))
        
        # Extract card type from payment method title if not in meta
        payment_method_title = order.get('payment_method_title', 'N/A')
        if not card_type and payment_method_title:
            # Check if card brand is in the title
            for brand in ['Visa', 'Mastercard', 'American Express', 'Amex', 'Discover', 'Diners', 'JCB']:
                if brand.lower() in payment_method_title.lower():
                    card_type = brand
                    break
        
        details = f"{'='*70}\n"
        details += f"ORDER #{order['id']}\n"
        details += f"{'='*70}\n\n"
        details += f"📅 Date: {order_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
        details += f"📊 Status: {order['status'].upper()}\n"
        details += f"💳 Payment: {payment_method_title}\n"
        
        # Show card type if available
        if card_type:
            details += f"💳 Card Type: {card_type.upper()}\n"
        if card_last4:
            details += f"💳 Card Last 4: ****{card_last4}\n"
        
        # Shipping method
        shipping_lines = order.get('shipping_lines', [])
        if shipping_lines:
            details += f"🚚 Shipping: {shipping_lines[0]['method_title']}\n"
        
        details += f"\n{'='*70}\n"
        details += f"👤 CUSTOMER INFORMATION\n"
        details += f"{'='*70}\n"
        details += f"Name: {billing.get('first_name', '')} {billing.get('last_name', '')}\n"
        details += f"Email: {billing.get('email', '')}\n"
        details += f"Phone: {billing.get('phone', '')}\n"
        details += f"Company: {billing.get('company', 'N/A')}\n"
        
        if vat_number:
            details += f"\n📋 VAT NUMBER (ΑΦΜ): {vat_number}\n"
            details += f"✓ INVOICE REQUESTED\n"
        
        details += f"\n{'='*70}\n"
        details += f"📍 BILLING ADDRESS\n"
        details += f"{'='*70}\n"
        details += f"{billing.get('address_1', '')}\n"
        if billing.get('address_2'):
            details += f"{billing['address_2']}\n"
        details += f"{billing.get('postcode', '')} {billing.get('city', '')}\n"
        details += f"{billing.get('country', '')}\n"
        
        details += f"\n{'='*70}\n"
        details += f"📦 SHIPPING ADDRESS\n"
        details += f"{'='*70}\n"
        details += f"{shipping.get('address_1', '')}\n"
        if shipping.get('address_2'):
            details += f"{shipping['address_2']}\n"
        details += f"{shipping.get('postcode', '')} {shipping.get('city', '')}\n"
        details += f"{shipping.get('country', '')}\n"
        
        details += f"\n{'='*70}\n"
        details += f"🛒 ORDER ITEMS\n"
        details += f"{'='*70}\n"
        
        for idx, item in enumerate(order['line_items'], 1):
            details += f"\n{idx}. {item['name']}\n"
            details += f"   SKU: {item.get('sku', 'N/A')}\n"
            details += f"   Qty: {item['quantity']} x €{float(item['price']):.2f} = €{float(item['total']):.2f}\n"
        
        # Shipping cost
        if shipping_lines:
            details += f"\n{'─'*70}\n"
            details += f"Shipping: €{float(shipping_lines[0]['total']):.2f}\n"
        
        # Tax
        details += f"Tax: €{float(order.get('total_tax', 0)):.2f}\n"
        
        details += f"\n{'='*70}\n"
        details += f"💰 TOTAL: €{float(order['total']):.2f}\n"
        details += f"{'='*70}\n"
        
        # Customer order history
        customer_email = billing.get('email')
        if customer_email and customer_email in self.customer_data:
            customer = self.customer_data[customer_email]
            details += f"\n{'='*70}\n"
            details += f"📊 CUSTOMER HISTORY\n"
            details += f"{'='*70}\n"
            details += f"Total Orders: {customer['order_count']}\n"
            details += f"Total Spent: €{customer['total_spent']:,.2f}\n"
            details += f"Customer Type: {'NEW' if customer['order_count'] == 1 else 'RETURNING'}\n"
        
        text.insert('1.0', details)
        text.config(state='disabled')
        
    def start_refresh_countdown(self):
        """Start the auto-refresh countdown timer"""
        self.seconds_until_refresh = self.refresh_interval
        self.update_countdown()
        
    def update_countdown(self):
        """Update the countdown display"""
        if self.seconds_until_refresh <= 0:
            # Time to refresh
            self.log("🔄 Auto-refresh: Reloading all data...")
            self.load_all_data()
            self.seconds_until_refresh = self.refresh_interval
        
        # Format time
        minutes = self.seconds_until_refresh // 60
        seconds = self.seconds_until_refresh % 60
        self.refresh_label.config(text=f"⏱️ Next refresh in: {minutes:02d}:{seconds:02d}")
        
        self.seconds_until_refresh -= 1
        
        # Schedule next update
        self.refresh_timer = self.root.after(1000, self.update_countdown)
        
    def export_products(self):
        """Export products to CSV"""
        filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'SKU', 'Name', 'Price', 'Stock Qty', 'Stock Status'])
            
            for product in self.all_products:
                writer.writerow([
                    product['id'],
                    product.get('sku', 'N/A'),
                    product['name'],
                    product.get('regular_price', product.get('price', '0')),
                    product.get('stock_quantity', 'N/A'),
                    product.get('stock_status', 'N/A')
                ])
        
        self.log(f"📊 Exported products to {filename}")
        messagebox.showinfo("Export", f"Exported {len(self.all_products)} products to:\n{filename}")
        
    def export_orders(self):
        """Export orders to CSV"""
        filename = f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Order ID', 'Date', 'Customer', 'Email', 'Phone', 
                           'Payment', 'Shipping', 'VAT Number', 'Total', 'Status'])
            
            for order in self.all_orders:
                billing = order.get('billing', {})
                
                # Get VAT number
                meta_data = order.get('meta_data', [])
                vat_number = ''
                for meta in meta_data:
                    if meta.get('key') == '_billing_vat_number':
                        vat_number = meta.get('value', '')
                        break
                
                # Get shipping method
                shipping_lines = order.get('shipping_lines', [])
                shipping_method = shipping_lines[0]['method_title'] if shipping_lines else 'N/A'
                
                writer.writerow([
                    order['id'],
                    order['date_created'].split('T')[0],
                    f"{billing.get('first_name', '')} {billing.get('last_name', '')}",
                    billing.get('email', ''),
                    billing.get('phone', ''),
                    order.get('payment_method_title', 'N/A'),
                    shipping_method,
                    vat_number,
                    order['total'],
                    order['status']
                ])
        
        self.log(f"📊 Exported orders to {filename}")
        messagebox.showinfo("Export", f"Exported {len(self.all_orders)} orders to:\n{filename}")
        
    def export_customers(self):
        """Export customer analytics to CSV"""
        filename = f"customers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Customer', 'Email', 'Phone', 'Orders', 'Total Spent', 
                           'Avg Order', 'Type', 'Last Order'])
            
            for item in self.customers_tree.get_children():
                values = self.customers_tree.item(item)['values']
                writer.writerow(values)
        
        self.log(f"📊 Exported customer analytics to {filename}")
        messagebox.showinfo("Export", f"Exported customer data to:\n{filename}")
        
    def export_performance(self):
        """Export product performance to CSV"""
        filename = f"product_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Rank', 'SKU', 'Product Name', 'Times Sold', 
                           'Total Qty', 'Revenue', 'Avg Price'])
            
            for item in self.performance_tree.get_children():
                values = self.performance_tree.item(item)['values']
                writer.writerow(values)
        
        self.log(f"📊 Exported product performance to {filename}")
        messagebox.showinfo("Export", f"Exported performance data to:\n{filename}")

def main():
    root = tk.Tk()
    app = EnhancedWooCommerceDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
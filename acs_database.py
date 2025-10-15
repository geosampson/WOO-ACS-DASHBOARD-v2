"""
SQLite Database for ACS Shipments
Stores shipment history, tracking, and pickup lists
WITH PDF PATH SUPPORT - Auto PDF save workflow
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple


class ACSDatabase:
    """SQLite database handler for ACS shipments"""
    
    def __init__(self, db_path: str = "shipments.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
        self.upgrade_database()  # Add any new columns if needed
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Access columns by name
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        
        # Shipments table (WITH pdf_path column)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_no TEXT UNIQUE,
                source TEXT NOT NULL,
                woocommerce_order_id INTEGER,
                manual_reference TEXT,
                
                recipient_name TEXT NOT NULL,
                recipient_address TEXT NOT NULL,
                recipient_city TEXT NOT NULL,
                recipient_zipcode TEXT NOT NULL,
                recipient_phone TEXT NOT NULL,
                recipient_email TEXT,
                
                weight REAL,
                pieces INTEGER DEFAULT 1,
                cod_amount REAL DEFAULT 0,
                
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                pickup_date DATE,
                pickup_list_no TEXT,
                
                status TEXT DEFAULT 'DRAFT',
                tracking_data TEXT,
                notes TEXT,
                pdf_path TEXT,
                
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Pickup lists table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS pickup_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pickup_list_no TEXT UNIQUE,
                pickup_date DATE NOT NULL,
                total_vouchers INTEGER DEFAULT 0,
                eshop_count INTEGER DEFAULT 0,
                manual_count INTEGER DEFAULT 0,
                
                status TEXT DEFAULT 'PENDING',
                pickup_time TEXT DEFAULT '10:00',
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                picked_up_at DATETIME
            )
        """)
        
        # Activity log table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                voucher_no TEXT,
                details TEXT,
                user TEXT DEFAULT 'system'
            )
        """)
        
        self.conn.commit()
    
    def upgrade_database(self):
        """Add pdf_path column if it doesn't exist (for existing databases)"""
        try:
            # Check if pdf_path column exists
            self.cursor.execute("PRAGMA table_info(shipments)")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            if 'pdf_path' not in columns:
                print("📝 Upgrading database: Adding pdf_path column...")
                self.cursor.execute("ALTER TABLE shipments ADD COLUMN pdf_path TEXT")
                self.conn.commit()
                print("✅ Database upgraded successfully!")
        except Exception as e:
            print(f"Note: Database upgrade check: {e}")
    
    def add_shipment(self, data: Dict) -> int:
        """Add new shipment to database"""
        try:
            self.cursor.execute("""
                INSERT INTO shipments (
                    voucher_no, source, woocommerce_order_id, manual_reference,
                    recipient_name, recipient_address, recipient_city, 
                    recipient_zipcode, recipient_phone, recipient_email,
                    weight, pieces, cod_amount, status, notes, pdf_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('voucher_no'),
                data['source'],
                data.get('woocommerce_order_id'),
                data.get('manual_reference'),
                data['recipient_name'],
                data['recipient_address'],
                data['recipient_city'],
                data['recipient_zipcode'],
                data['recipient_phone'],
                data.get('recipient_email', ''),
                data.get('weight', 1.0),
                data.get('pieces', 1),
                data.get('cod_amount', 0),
                data.get('status', 'DRAFT'),
                data.get('notes', ''),
                data.get('pdf_path')  # NEW: PDF path storage
            ))
            
            self.conn.commit()
            shipment_id = self.cursor.lastrowid
            
            # Log activity
            self.log_activity(
                'CREATE_SHIPMENT',
                data.get('voucher_no'),
                f"Created shipment for {data['recipient_name']}"
            )
            
            return shipment_id
            
        except Exception as e:
            print(f"Error adding shipment: {e}")
            return None
    
    def update_shipment(self, shipment_id: int, data: Dict):
        """Update existing shipment"""
        try:
            # Build UPDATE query dynamically based on provided fields
            fields = []
            values = []
            
            for key, value in data.items():
                if key != 'id':
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if not fields:
                return
            
            # Add last_updated
            fields.append("last_updated = CURRENT_TIMESTAMP")
            
            query = f"UPDATE shipments SET {', '.join(fields)} WHERE id = ?"
            values.append(shipment_id)
            
            self.cursor.execute(query, values)
            self.conn.commit()
            
        except Exception as e:
            print(f"Error updating shipment: {e}")
    
    def get_shipment(self, shipment_id: int = None, voucher_no: str = None) -> Optional[Dict]:
        """Get shipment by ID or voucher number"""
        try:
            if shipment_id:
                self.cursor.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
            elif voucher_no:
                self.cursor.execute("SELECT * FROM shipments WHERE voucher_no = ?", (voucher_no,))
            else:
                return None
            
            row = self.cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            print(f"Error getting shipment: {e}")
            return None
    
    def get_all_shipments(self, filters: Dict = None) -> List[Dict]:
        """Get all shipments with optional filters"""
        try:
            query = "SELECT * FROM shipments WHERE 1=1"
            params = []
            
            if filters:
                if 'source' in filters:
                    query += " AND source = ?"
                    params.append(filters['source'])
                
                if 'status' in filters:
                    query += " AND status = ?"
                    params.append(filters['status'])
                
                if 'woocommerce_order_id' in filters:
                    query += " AND woocommerce_order_id = ?"
                    params.append(filters['woocommerce_order_id'])
                
                if 'date_from' in filters:
                    query += " AND DATE(created_date) >= ?"
                    params.append(filters['date_from'].strftime('%Y-%m-%d'))
                
                if 'date_to' in filters:
                    query += " AND DATE(created_date) <= ?"
                    params.append(filters['date_to'].strftime('%Y-%m-%d'))
                
                if 'has_voucher' in filters:
                    if filters['has_voucher']:
                        query += " AND voucher_no IS NOT NULL"
                    else:
                        query += " AND voucher_no IS NULL"
            
            query += " ORDER BY created_date DESC"
            
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Error getting shipments: {e}")
            return []
    
    def get_today_stats(self) -> Dict:
        """Get today's statistics"""
        try:
            today = date.today().strftime('%Y-%m-%d')
            
            # Total shipments today
            self.cursor.execute("""
                SELECT COUNT(*) FROM shipments 
                WHERE DATE(created_date) = ?
            """, (today,))
            total = self.cursor.fetchone()[0]
            
            # E-shop orders
            self.cursor.execute("""
                SELECT COUNT(*) FROM shipments 
                WHERE DATE(created_date) = ? AND source = 'ESHOP'
            """, (today,))
            eshop = self.cursor.fetchone()[0]
            
            # Manual entries
            self.cursor.execute("""
                SELECT COUNT(*) FROM shipments 
                WHERE DATE(created_date) = ? AND source = 'MANUAL'
            """, (today,))
            manual = self.cursor.fetchone()[0]
            
            # Ready for pickup
            self.cursor.execute("""
                SELECT COUNT(*) FROM shipments 
                WHERE DATE(created_date) = ? AND status = 'READY'
            """, (today,))
            ready = self.cursor.fetchone()[0]
            
            return {
                'total': total,
                'eshop': eshop,
                'manual': manual,
                'ready': ready
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {'total': 0, 'eshop': 0, 'manual': 0, 'ready': 0}
    
    def create_pickup_list(self) -> Tuple[int, Dict]:
        """Create pickup list for today's ready shipments"""
        try:
            today = date.today()
            today_str = today.strftime('%Y-%m-%d')
            
            # Get today's statistics
            stats = self.get_today_stats()
            
            # Generate pickup list number (format: YYYYMMDDXXXX)
            self.cursor.execute("""
                SELECT COUNT(*) FROM pickup_lists 
                WHERE pickup_date = ?
            """, (today_str,))
            count = self.cursor.fetchone()[0]
            
            pickup_list_no = f"{today.strftime('%Y%m%d')}{count+1:04d}"
            
            # Create pickup list
            self.cursor.execute("""
                INSERT INTO pickup_lists (
                    pickup_list_no, pickup_date, 
                    total_vouchers, eshop_count, manual_count
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                pickup_list_no,
                today_str,
                stats['total'],
                stats['eshop'],
                stats['manual']
            ))
            
            list_id = self.cursor.lastrowid
            
            # Update shipments with pickup list number
            self.cursor.execute("""
                UPDATE shipments 
                SET pickup_list_no = ?, 
                    pickup_date = ?,
                    status = 'PICKED_UP'
                WHERE DATE(created_date) = ? AND status = 'READY'
            """, (pickup_list_no, today_str, today_str))
            
            self.conn.commit()
            
            # Log activity
            self.log_activity(
                'CREATE_PICKUP_LIST',
                None,
                f"Created pickup list {pickup_list_no} with {stats['total']} shipments"
            )
            
            return list_id, {
                'pickup_list_no': pickup_list_no,
                'total_vouchers': stats['total'],
                'eshop_count': stats['eshop'],
                'manual_count': stats['manual']
            }
            
        except Exception as e:
            print(f"Error creating pickup list: {e}")
            return None, {}
    
    def get_pickup_list(self, pickup_list_no: str = None, 
                       pickup_date: date = None) -> Optional[Dict]:
        """Get pickup list by number or date"""
        try:
            if pickup_list_no:
                self.cursor.execute("""
                    SELECT * FROM pickup_lists WHERE pickup_list_no = ?
                """, (pickup_list_no,))
            elif pickup_date:
                self.cursor.execute("""
                    SELECT * FROM pickup_lists WHERE pickup_date = ?
                """, (pickup_date.strftime('%Y-%m-%d'),))
            else:
                return None
            
            row = self.cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            print(f"Error getting pickup list: {e}")
            return None
    
    def log_activity(self, action: str, voucher_no: str = None, 
                    details: str = None):
        """Log activity to database"""
        try:
            self.cursor.execute("""
                INSERT INTO activity_log (action, voucher_no, details)
                VALUES (?, ?, ?)
            """, (action, voucher_no, details))
            self.conn.commit()
        except Exception as e:
            print(f"Error logging activity: {e}")
    
    def get_activity_log(self, limit: int = 100, 
                        date_from: date = None) -> List[Dict]:
        """Get activity log"""
        try:
            query = "SELECT * FROM activity_log WHERE 1=1"
            params = []
            
            if date_from:
                query += " AND DATE(timestamp) >= ?"
                params.append(date_from.strftime('%Y-%m-%d'))
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Error getting activity log: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Test database connection
if __name__ == "__main__":
    print("Testing ACS Database...")
    
    db = ACSDatabase()
    
    # Test connection
    if db.conn:
        print("✅ Database connected")
        print(f"✅ Tables created")
        
        # Get today's stats
        stats = db.get_today_stats()
        print(f"📊 Today's stats: {stats}")
        
        # Check if pdf_path column exists
        db.cursor.execute("PRAGMA table_info(shipments)")
        columns = [col[1] for col in db.cursor.fetchall()]
        if 'pdf_path' in columns:
            print("✅ pdf_path column exists - ready for auto PDF save!")
        else:
            print("❌ pdf_path column missing")
    else:
        print("❌ Database connection failed")
    
    db.close()
    print("\nDatabase test complete!")
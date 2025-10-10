"""
SQLite Database for ACS Shipments
Stores shipment history, tracking, and pickup lists
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
        
        # Shipments table
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
    
    # ==================== SHIPMENTS ====================
    
    def add_shipment(self, shipment_data: Dict) -> int:
        """
        Add new shipment to database
        
        Returns:
            Shipment ID
        """
        try:
            self.cursor.execute("""
                INSERT INTO shipments (
                    voucher_no, source, woocommerce_order_id, manual_reference,
                    recipient_name, recipient_address, recipient_city, 
                    recipient_zipcode, recipient_phone, recipient_email,
                    weight, pieces, cod_amount, notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                shipment_data.get('voucher_no'),
                shipment_data['source'],
                shipment_data.get('woocommerce_order_id'),
                shipment_data.get('manual_reference'),
                shipment_data['recipient_name'],
                shipment_data['recipient_address'],
                shipment_data['recipient_city'],
                shipment_data['recipient_zipcode'],
                shipment_data['recipient_phone'],
                shipment_data.get('recipient_email'),
                shipment_data.get('weight', 1.0),
                shipment_data.get('pieces', 1),
                shipment_data.get('cod_amount', 0),
                shipment_data.get('notes'),
                shipment_data.get('status', 'DRAFT')
            ))
            
            self.conn.commit()
            shipment_id = self.cursor.lastrowid
            
            self.log_activity(
                'SHIPMENT_CREATED',
                shipment_data.get('voucher_no'),
                f"Source: {shipment_data['source']}"
            )
            
            return shipment_id
            
        except Exception as e:
            print(f"Error adding shipment: {e}")
            return None
    
    def update_shipment(self, shipment_id: int, updates: Dict) -> bool:
        """Update shipment fields"""
        try:
            # Build UPDATE query dynamically
            fields = []
            values = []
            
            for key, value in updates.items():
                fields.append(f"{key} = ?")
                values.append(value)
            
            # Always update last_updated
            fields.append("last_updated = CURRENT_TIMESTAMP")
            values.append(shipment_id)
            
            query = f"UPDATE shipments SET {', '.join(fields)} WHERE id = ?"
            
            self.cursor.execute(query, values)
            self.conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Error updating shipment: {e}")
            return False
    
    def get_shipment(self, shipment_id: int = None, voucher_no: str = None) -> Dict:
        """Get shipment by ID or voucher number"""
        try:
            if shipment_id:
                self.cursor.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
            elif voucher_no:
                self.cursor.execute("SELECT * FROM shipments WHERE voucher_no = ?", (voucher_no,))
            else:
                return None
            
            row = self.cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            print(f"Error getting shipment: {e}")
            return None
    
    def get_all_shipments(self, filters: Dict = None) -> List[Dict]:
        """
        Get all shipments with optional filters
        
        Filters:
            - source: 'ESHOP' or 'MANUAL'
            - status: shipment status
            - date_from: from date
            - date_to: to date
            - has_voucher: True/False
        """
        try:
            query = "SELECT * FROM shipments WHERE 1=1"
            params = []
            
            if filters:
                if filters.get('source'):
                    query += " AND source = ?"
                    params.append(filters['source'])
                
                if filters.get('status'):
                    query += " AND status = ?"
                    params.append(filters['status'])
                
                if filters.get('date_from'):
                    query += " AND DATE(created_date) >= ?"
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    query += " AND DATE(created_date) <= ?"
                    params.append(filters['date_to'])
                
                if filters.get('has_voucher') is not None:
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
    
    def delete_shipment(self, shipment_id: int) -> bool:
        """Delete shipment (only if no voucher created)"""
        try:
            # Check if voucher exists
            shipment = self.get_shipment(shipment_id=shipment_id)
            if shipment and shipment.get('voucher_no'):
                print("Cannot delete shipment with voucher. Cancel voucher first.")
                return False
            
            self.cursor.execute("DELETE FROM shipments WHERE id = ?", (shipment_id,))
            self.conn.commit()
            
            self.log_activity('SHIPMENT_DELETED', None, f"Shipment ID: {shipment_id}")
            
            return True
            
        except Exception as e:
            print(f"Error deleting shipment: {e}")
            return False
    
    # ==================== PICKUP LISTS ====================
    
    def create_pickup_list(self, pickup_date: date = None) -> Tuple[int, str]:
        """
        Create new pickup list
        
        Returns:
            (list_id, pickup_list_no)
        """
        try:
            if not pickup_date:
                pickup_date = date.today()
            
            # Generate pickup list number (format: date + counter)
            date_str = pickup_date.strftime('%Y%m%d')
            
            # Check existing lists for today
            self.cursor.execute("""
                SELECT COUNT(*) FROM pickup_lists 
                WHERE pickup_date = ?
            """, (pickup_date,))
            
            count = self.cursor.fetchone()[0]
            pickup_list_no = f"{date_str}_{count + 1:02d}"
            
            # Count shipments for today
            shipments = self.get_all_shipments({
                'date_from': pickup_date,
                'date_to': pickup_date,
                'has_voucher': True
            })
            
            eshop_count = sum(1 for s in shipments if s['source'] == 'ESHOP')
            manual_count = sum(1 for s in shipments if s['source'] == 'MANUAL')
            
            self.cursor.execute("""
                INSERT INTO pickup_lists (
                    pickup_list_no, pickup_date, 
                    total_vouchers, eshop_count, manual_count
                ) VALUES (?, ?, ?, ?, ?)
            """, (pickup_list_no, pickup_date, len(shipments), eshop_count, manual_count))
            
            self.conn.commit()
            list_id = self.cursor.lastrowid
            
            # Update shipments with pickup list number
            for shipment in shipments:
                self.update_shipment(shipment['id'], {
                    'pickup_list_no': pickup_list_no,
                    'pickup_date': pickup_date,
                    'status': 'READY'
                })
            
            self.log_activity(
                'PICKUP_LIST_CREATED',
                None,
                f"List: {pickup_list_no}, Shipments: {len(shipments)}"
            )
            
            return list_id, pickup_list_no
            
        except Exception as e:
            print(f"Error creating pickup list: {e}")
            return None, None
    
    def get_pickup_list(self, pickup_list_no: str) -> Dict:
        """Get pickup list details"""
        try:
            self.cursor.execute("""
                SELECT * FROM pickup_lists WHERE pickup_list_no = ?
            """, (pickup_list_no,))
            
            row = self.cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            print(f"Error getting pickup list: {e}")
            return None
    
    def get_pickup_list_shipments(self, pickup_list_no: str) -> List[Dict]:
        """Get all shipments in a pickup list"""
        return self.get_all_shipments({'pickup_list_no': pickup_list_no})
    
    def mark_pickup_completed(self, pickup_list_no: str) -> bool:
        """Mark pickup as completed"""
        try:
            self.cursor.execute("""
                UPDATE pickup_lists 
                SET status = 'PICKED_UP',
                    picked_up_at = CURRENT_TIMESTAMP
                WHERE pickup_list_no = ?
            """, (pickup_list_no,))
            
            # Update all shipments in this list
            self.cursor.execute("""
                UPDATE shipments
                SET status = 'PICKED_UP'
                WHERE pickup_list_no = ?
            """, (pickup_list_no,))
            
            self.conn.commit()
            
            self.log_activity(
                'PICKUP_COMPLETED',
                None,
                f"Pickup list: {pickup_list_no}"
            )
            
            return True
            
        except Exception as e:
            print(f"Error marking pickup completed: {e}")
            return False
    
    # ==================== STATISTICS ====================
    
    def get_today_stats(self) -> Dict:
        """Get today's shipment statistics"""
        today = date.today()
        
        shipments = self.get_all_shipments({
            'date_from': today,
            'date_to': today
        })
        
        return {
            'total': len(shipments),
            'eshop': sum(1 for s in shipments if s['source'] == 'ESHOP'),
            'manual': sum(1 for s in shipments if s['source'] == 'MANUAL'),
            'with_voucher': sum(1 for s in shipments if s['voucher_no']),
            'ready': sum(1 for s in shipments if s['status'] == 'READY'),
            'picked_up': sum(1 for s in shipments if s['status'] == 'PICKED_UP'),
            'total_cod': sum(s['cod_amount'] for s in shipments if s['cod_amount'])
        }
    
    def get_period_stats(self, days: int = 30) -> Dict:
        """Get statistics for last N days"""
        date_from = date.today() - timedelta(days=days)
        
        shipments = self.get_all_shipments({
            'date_from': date_from
        })
        
        return {
            'total_shipments': len(shipments),
            'eshop_orders': sum(1 for s in shipments if s['source'] == 'ESHOP'),
            'manual_entries': sum(1 for s in shipments if s['source'] == 'MANUAL'),
            'total_cod_collected': sum(s['cod_amount'] for s in shipments if s['cod_amount']),
            'average_per_day': len(shipments) / days
        }
    
    # ==================== ACTIVITY LOG ====================
    
    def log_activity(self, action: str, voucher_no: str = None, details: str = None):
        """Log activity to database"""
        try:
            self.cursor.execute("""
                INSERT INTO activity_log (action, voucher_no, details)
                VALUES (?, ?, ?)
            """, (action, voucher_no, details))
            
            self.conn.commit()
            
        except Exception as e:
            print(f"Error logging activity: {e}")
    
    def get_recent_activity(self, limit: int = 50) -> List[Dict]:
        """Get recent activity log"""
        try:
            self.cursor.execute("""
                SELECT * FROM activity_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Error getting activity log: {e}")
            return []
    
    # ==================== CLEANUP ====================
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
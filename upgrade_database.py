"""
Database Update Script - Add PDF Path Storage
Run this ONCE to update your existing database
"""

import sqlite3

def upgrade_database(db_path="shipments.db"):
    """Add pdf_path column to shipments table"""
    
    print("="*60)
    print("DATABASE UPGRADE SCRIPT")
    print("="*60)
    print(f"\nDatabase: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(shipments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'pdf_path' in columns:
            print("\n✅ Database already has 'pdf_path' column - no update needed")
            return True
        
        print("\n📝 Adding 'pdf_path' column to shipments table...")
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE shipments 
            ADD COLUMN pdf_path TEXT
        """)
        
        conn.commit()
        
        print("✅ Database updated successfully!")
        print("\nNew column added: pdf_path (TEXT)")
        print("This will store the local path to saved voucher PDFs")
        
        # Verify
        cursor.execute("PRAGMA table_info(shipments)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"\nTotal columns in shipments table: {len(columns)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error updating database: {e}")
        return False


if __name__ == "__main__":
    success = upgrade_database()
    
    if success:
        print("\n" + "="*60)
        print("✅ UPGRADE COMPLETE")
        print("="*60)
        print("\nYou can now:")
        print("1. Store PDF paths when vouchers are created")
        print("2. Track which vouchers have saved PDFs")
        print("3. Show users if PDFs were already saved")
    else:
        print("\n" + "="*60)
        print("❌ UPGRADE FAILED")
        print("="*60)
        print("\nPlease check the error message above")

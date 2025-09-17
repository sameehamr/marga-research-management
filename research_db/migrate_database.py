#!/usr/bin/env python3
"""
Database Migration Script
Adds missing columns to existing database tables
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Add missing columns to the database"""
    
    # Get database path - check both locations
    possible_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'research_projects.db'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'research_projects.db')
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print(f"Database not found in any of these locations: {possible_paths}")
        return False
    
    print(f"Migrating database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(project)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        # Check if audit_log table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
        audit_table_exists = cursor.fetchone() is not None
        
        if not audit_table_exists:
            print("Creating audit_log table...")
            cursor.execute("""
                CREATE TABLE audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action VARCHAR(100) NOT NULL,
                    resource_type VARCHAR(50),
                    resource_id VARCHAR(100),
                    details TEXT,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES user (id)
                )
            """)
            print("✅ Created audit_log table")
        else:
            print("✅ audit_log table already exists")
        
        # Check if project_status_history table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_status_history'")
        status_history_table_exists = cursor.fetchone() is not None
        
        if not status_history_table_exists:
            print("Creating project_status_history table...")
            cursor.execute("""
                CREATE TABLE project_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    from_status VARCHAR(20),
                    to_status VARCHAR(20) NOT NULL,
                    reason TEXT,
                    changed_at DATETIME NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES project (id),
                    FOREIGN KEY (user_id) REFERENCES user (id)
                )
            """)
            print("✅ Created project_status_history table")
        else:
            print("✅ project_status_history table already exists")
        
        # Add missing columns
        columns_to_add = [
            ('currency', 'VARCHAR(10) DEFAULT "Rs"'),
            ('category', 'VARCHAR(100)'),
            ('theme', 'VARCHAR(100)')
        ]
        
        for column_name, column_def in columns_to_add:
            if column_name not in columns:
                try:
                    sql = f"ALTER TABLE project ADD COLUMN {column_name} {column_def}"
                    print(f"Adding column: {sql}")
                    cursor.execute(sql)
                    print(f"✅ Added column: {column_name}")
                except sqlite3.Error as e:
                    print(f"❌ Error adding column {column_name}: {e}")
            else:
                print(f"✅ Column {column_name} already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(project)")
        new_columns = [row[1] for row in cursor.fetchall()]
        print(f"Updated columns: {new_columns}")
        
        conn.close()
        print("✅ Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    migrate_database()
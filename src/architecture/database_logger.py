import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'execution_logs.db')

def init_db():
    """Initializes the SQLite database schema to log tasks and execution times."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the tasks execution log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            execution_time_ms INTEGER,
            status TEXT DEFAULT 'running',
            cloud_cost_saved_usd REAL DEFAULT 0.0,
            notes TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def log_task_start(task_name):
    """Logs the start of a task and returns the task ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    start_time = datetime.now()
    cursor.execute('''
        INSERT INTO execution_logs (task_name, start_time, status)
        VALUES (?, ?, 'running')
    ''', (task_name, start_time))
    
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id, start_time

def log_task_end(task_id, start_time, cloud_cost_saved_usd=0.0, notes=""):
    """Logs the end of a task and calculates execution time."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    end_time = datetime.now()
    execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
    
    cursor.execute('''
        UPDATE execution_logs
        SET end_time = ?, execution_time_ms = ?, status = 'completed', cloud_cost_saved_usd = ?, notes = ?
        WHERE id = ?
    ''', (end_time, execution_time_ms, cloud_cost_saved_usd, notes, task_id))
    
    conn.commit()
    conn.close()
    return execution_time_ms

if __name__ == "__main__":
    init_db()

import sqlite3
import os
from datetime import datetime, timezone

# [Requirement] Use Environment Variable for DB path.
# This allows Docker to inject a persistent path like "/data/app.db"
# If not set, it defaults to "app.db" for local testing.
DB_PATH = os.getenv("DATABASE_URL", "app.db").replace("sqlite:///", "")

def init_db():
    """
    Creates the table if it doesn't exist.
    [Requirement] Schema must match the specific columns in the PDF.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,   -- [Requirement] Primary Key enforces Idempotency
            from_msisdn TEXT NOT NULL,
            to_msisdn TEXT NOT NULL,
            ts TEXT NOT NULL,
            text TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def insert_message(message_id, sender, receiver, ts, text):
    """
    Inserts a message. Returns True if new, False if duplicate.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        created_at = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at) 
            VALUES (?,?,?,?,?,?)
        """, (message_id, sender, receiver, ts, text, created_at))
        
        conn.commit()
        return True # Success: New message saved

    except sqlite3.IntegrityError:
        # [Requirement] Idempotency: "Must not insert a second row"
        # We catch the error and return False so the API knows it was a duplicate.
        return False
    finally:
        if conn:
            conn.close()

def get_messages(limit=50, offset=0, from_msisdn=None, since=None, text_search=None):
    """
    Retrieve a page of messages with dynamic filtering.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name: row['text']
    cursor = conn.cursor()

    # 1. Base Query with "1=1" trick (allows appending "AND..." easily)
    query = "FROM messages WHERE 1=1"
    params = []

    # 2. Dynamic Filters
    if from_msisdn:
        query += " AND from_msisdn = ?"
        params.append(from_msisdn)

    if since:
        query += " AND ts >= ?"
        params.append(since)

    if text_search:
        # [Requirement] "Content search" (substring match)
        query += " AND text LIKE ?"
        params.append(f"%{text_search}%")

    # 3. Get Total Count (Required for Pagination UI)
    count_query = f"SELECT COUNT(*) {query}"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]

    # 4. Get Actual Data
    # [Requirement] Ordering by timestamp and ID for consistent paging
    data_query = f"SELECT * {query} ORDER BY ts ASC, message_id ASC LIMIT ? OFFSET ?"
    final_params = params + [limit, offset]

    cursor.execute(data_query, final_params)
    rows = cursor.fetchall()
    conn.close()

    # 5. Format as list of dicts
    results = []
    for row in rows:
        results.append({
            "message_id": row["message_id"],
            "from": row["from_msisdn"],
            "to": row["to_msisdn"],
            "ts": row["ts"],
            "text": row["text"]
        })
        
    return results, total_count    

def get_stats():
    """
    Computes analytics using efficient SQL Aggregations.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query 1: Overall Summary
    cursor.execute(""" 
        SELECT 
            COUNT(*) as total_msg, 
            COUNT(DISTINCT from_msisdn) as total_senders, 
            MIN(ts) as first_ts, 
            MAX(ts) as last_ts 
        FROM messages
    """)
    summary = cursor.fetchone()

    # Query 2: Top 10 Senders (The Leaderboard)
    cursor.execute(""" 
        SELECT from_msisdn, COUNT(*) as msg_count 
        FROM messages 
        GROUP BY from_msisdn 
        ORDER BY msg_count DESC 
        LIMIT 10
    """)
    top_senders_rows = cursor.fetchall()
    conn.close()

    senders_list = []
    for row in top_senders_rows:
        senders_list.append({
            "from": row["from_msisdn"],
            "count": row["msg_count"]
        })
        
    return {
        "total_messages": summary["total_msg"],
        "senders_count": summary["total_senders"],
        "messages_per_sender": senders_list,
        "first_message_ts": summary["first_ts"],
        "last_message_ts": summary["last_ts"]
    }

def check_db():
    """Health check: Returns True if DB is reachable."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False
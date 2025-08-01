import psycopg2
import psycopg2.extras # <--- ADD THIS LINE
from typing import List, Dict, Any, Optional
from datetime import date
from api.database import get_db_connection
import logging


logger = logging.getLogger(__name__)

# --- Helper function to fetch data ---
def fetch_data(query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """Executes a SQL query and returns results as a list of dictionaries."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) # Returns rows as dicts
        cursor.execute(query, params)
        results = cursor.fetchall()
        return results
    except Exception as e:
        logger.error(f"Database query failed: {query} with params {params}. Error: {e}", exc_info=True)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# --- Analytical Query Functions ---

def get_top_products(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Returns the top N most frequently mentioned medical products/keywords.
    """
    # Using a list of keywords to construct the WHERE clause dynamically
    product_keywords_list = [
        'paracetamol', 'amoxicillin', 'ibuprofen', 'azithromycin', 'omeprazole',
        'cream', 'tablet', 'syrup', 'injection', 'vitamin', 'antibiotic',
        'ointment', 'drops', 'capsule', 'suspension', 'vaccine', 'mask',
        'sanitizer', 'gloves', 'thermometer', 'blood pressure monitor'
    ]

    # Construct the ILIKE conditions dynamically
    # This avoids potential issues with long static strings or hidden characters
    # and ensures correct parameter handling if you were to parameterize each ILIKE
    like_conditions = [f"fm.message_text ILIKE %s" for _ in product_keywords_list]
    where_clause_parts = " OR ".join(like_conditions)

    # The parameters for the ILIKE conditions
    # Each keyword needs to be wrapped in %%, so we create a list of parameters
    # This is why the IndexError occurs: the query has many %s, but params only has one.
    # We need a parameter for EACH %s in the WHERE clause.
    like_params = [f"%{keyword}%" for keyword in product_keywords_list]

    query = f"""
    WITH ProductMentions AS (
        SELECT
            CASE
                -- Add more WHEN clauses for specific product keywords
                WHEN fm.message_text ILIKE '%paracetamol%' THEN 'Paracetamol'
                WHEN fm.message_text ILIKE '%amoxicillin%' THEN 'Amoxicillin'
                WHEN fm.message_text ILIKE '%ibuprofen%' THEN 'Ibuprofen'
                WHEN fm.message_text ILIKE '%cream%' THEN 'Cream'
                WHEN fm.message_text ILIKE '%tablet%' THEN 'Tablet'
                WHEN fm.message_text ILIKE '%syrup%' THEN 'Syrup'
                WHEN fm.message_text ILIKE '%injection%' THEN 'Injection'
                WHEN fm.message_text ILIKE '%vitamin%' THEN 'Vitamin'
                WHEN fm.message_text ILIKE '%antibiotic%' THEN 'Antibiotic'
                WHEN fm.message_text ILIKE '%ointment%' THEN 'Ointment'
                WHEN fm.message_text ILIKE '%drops%' THEN 'Drops'
                WHEN fm.message_text ILIKE '%capsule%' THEN 'Capsule'
                WHEN fm.message_text ILIKE '%vaccine%' THEN 'Vaccine'
                WHEN fm.message_text ILIKE '%mask%' THEN 'Mask'
                WHEN fm.message_text ILIKE '%sanitizer%' THEN 'Sanitizer'
                WHEN fm.message_text ILIKE '%gloves%' THEN 'Gloves'
                WHEN fm.message_text ILIKE '%thermometer%' THEN 'Thermometer'
                WHEN fm.message_text ILIKE '%blood pressure monitor%' THEN 'Blood Pressure Monitor'
                ELSE NULL
            END AS product_keyword
        FROM marts.fct_messages fm
        WHERE fm.message_text IS NOT NULL
          AND (
            {where_clause_parts} -- Dynamically insert the OR conditions
          )
    )
    SELECT
        product_keyword,
        COUNT(*) AS mention_count
    FROM ProductMentions
    WHERE product_keyword IS NOT NULL
    GROUP BY product_keyword
    ORDER BY mention_count DESC
    LIMIT %s;
    """
    # Combine all parameters: first the ILIKE parameters, then the LIMIT parameter
    all_params = tuple(like_params + [limit])
    return fetch_data(query, all_params)

def get_channel_activity(channel_name: str) -> List[Dict[str, Any]]:
    """
    Returns the daily posting activity for a specific channel.
    """
    query = """
    SELECT
        dd.date_day AS message_date,
        COUNT(fm.message_pk) AS message_count
    FROM marts.fct_messages fm
    JOIN marts.dim_channels dc ON fm.channel_id = dc.channel_id
    JOIN marts.dim_dates dd ON fm.date_key = dd.date_key
    WHERE dc.channel_username ILIKE %s
    GROUP BY dd.date_day
    ORDER BY dd.date_day;
    """
    return fetch_data(query, (channel_name,))

def search_messages(query_str: str) -> List[Dict[str, Any]]:
    """
    Searches for messages containing a specific keyword.
    """
    # Using ILIKE for case-insensitive search
    search_pattern = f"%{query_str}%"
    query = """
    SELECT
        fm.message_id,
        fm.message_text,
        dd.date_day AS message_date,
        dc.channel_name
    FROM marts.fct_messages fm
    JOIN marts.dim_channels dc ON fm.channel_id = dc.channel_id
    JOIN marts.dim_dates dd ON fm.date_key = dd.date_key
    WHERE fm.message_text ILIKE %s
    ORDER BY dd.date_day DESC, fm.message_id DESC
    LIMIT 100; -- Limit results to prevent very large responses
    """
    return fetch_data(query, (search_pattern,))
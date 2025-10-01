import psycopg2
from src.config import settings
import sys
def get_connection():

    """
    Get connection to the Postgres database.
    """
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        port=settings.POSTGRES_PORT
    )

def check_connection():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        val = cur.fetchone()
        cur.close()
        conn.close()
        if val and val[0] == 1:
            print("OK: Connected to database and query succeeded.")
            return 0
        else:
            print("ERROR: Query did not return expected result:", val)
            return 2
    except Exception as e:
        print("ERROR: Failed to connect or query database:", e)
        return 1

if __name__ == "__main__":
    sys.exit(check_connection())
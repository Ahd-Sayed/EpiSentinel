import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL not found in .env")

url = urllib.parse.urlparse(db_url)
user = url.username
password = url.password
host = url.hostname
port = url.port or 5432
dbname = url.path[1:]

print(f"Connecting to default postgres database at {host}:{port} with user {user}...")
conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host, port=port)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{dbname}'")
exists = cursor.fetchone()
if not exists:
    print(f"Database {dbname} does not exist. Creating...")
    cursor.execute(f"CREATE DATABASE {dbname};")
    print(f"Database {dbname} created successfully.")
else:
    print(f"Database {dbname} already exists.")

cursor.close()
conn.close()

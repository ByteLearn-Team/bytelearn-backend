import os                          # Import the os module to use environment variables (for secrets/passwords)
import mysql.connector             # Import the MySQL connector library for Python (lets us talk to MySQL databases)
from dotenv import load_dotenv     # Import function to load .env file variables

# Load environment variables from the .env file (this is where sensitive info like passwords is kept)
load_dotenv()

# Set up a connection to the MySQL database using all the secret info above
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),           # DB host address (where the database lives)
    port=os.getenv("DB_PORT"),           # DB port (like a door number for connecting)
    user=os.getenv("DB_USER"),           # Username to log in to DB
    password=os.getenv("DB_PASSWORD"),   # Password for logging in safely
    database=os.getenv("DB_NAME"),       # Which database to use
    ssl_disabled=False                   # Use SSL for encryption/securing your connection
)

# Check and print whether the DB connection worked
print(
    "✅ Connected to Aiven MySQL!" if conn.is_connected()
    else "❌ Failed to connect"
)

# Always close the connection when done (important to avoid leaks and errors!)
conn.close()

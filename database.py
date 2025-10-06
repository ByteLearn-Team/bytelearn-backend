# These are imports from SQLAlchemy, which is a popular Python library for working with databases
from sqlalchemy import create_engine            # Helps connect your app to a database (like MySQL)
from sqlalchemy.orm import sessionmaker, declarative_base   # Lets you create sessions (connections) and base class for your models
import os                                      # Lets us access environment variables/settings on the computer
from dotenv import load_dotenv                  # Lets us load values from a .env file (secrets, passwords, etc.)

# Load environment variables (used for things like database username/password)
load_dotenv()  # This makes sure .env file values are available

# Get all the database connection details from environment variables (with default values if nothing set)
DB_USER = os.getenv("DB_USER", "avnadmin")           # Username for the database
DB_PASSWORD = os.getenv("DB_PASSWORD", "AVNS_HkMiEJ9UMnVe02fD5zD")  # Database password — keep this secret!
DB_HOST = os.getenv("DB_HOST", "mysql-1560ef6d-bytlearn077.i.aivencloud.com") # Where the database is hosted (URL/address)
DB_PORT = os.getenv("DB_PORT", "16297")              # Port used to connect to the database
DB_NAME = os.getenv("DB_NAME", "defaultdb")          # Name of the actual database

# Build the full database URL that SQLAlchemy needs to connect (including username, password, host, etc.)
DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl_verify_cert=false"
)

# Create an 'engine' object to connect to MySQL using the above details
engine = create_engine(DATABASE_URL)

# SessionLocal lets us easily open/close a new database session for each request (much safer & more reliable)
SessionLocal = sessionmaker(
    bind=engine,          # Use the above engine (connection info)
    autocommit=False,     # Don't automatically save every change
    autoflush=False       # Don't automatically flush (update) every change until asked
)

# The 'Base' object is used by all our models/tables. Every table is a class that extends Base.
Base = declarative_base()

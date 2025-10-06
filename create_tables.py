# Import Base and engine from your database setup (defined in database.py)
from database import Base, engine

# Import all database models so SQLAlchemy knows what tables to create
import models  # This imports models.py (must be in the same folder!), so all tables are registered

# This function tells SQLAlchemy to create all tables needed for the app,
# based on your model classes inside models.py
def create_tables():
    print("📢 Creating tables in Aiven MySQL...")      # Print a message to show what's happening
    Base.metadata.create_all(bind=engine)              # Actually create all tables in the database!
    print("✅ All tables created successfully!")        # Print success message when done

# If you run this file directly (not by importing it), then create all tables immediately!
if __name__ == "__main__":
    create_tables()                                    # Run the function above to build all tables

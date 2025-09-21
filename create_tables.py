from database import Base, engine
import models  # make sure models.py is in the same folder

def create_tables():
    print("📢 Creating tables in Aiven MySQL...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")

if __name__ == "__main__":
    create_tables()

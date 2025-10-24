# Run this script ONCE after updating models.py to add the profile_picture column
# Save this as: add_profile_picture_column.py

from database import engine
from sqlalchemy import text

def add_profile_picture_column():
    """
    Add profile_picture column to students table
    """
    try:
        with engine.connect() as connection:
            # Check if column already exists
            result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'students' 
                AND COLUMN_NAME = 'profile_picture'
            """))
            
            exists = result.scalar()
            
            if exists == 0:
                # Add the column
                connection.execute(text("""
                    ALTER TABLE students 
                    ADD COLUMN profile_picture TEXT NULL
                """))
                connection.commit()
                print("✅ Successfully added profile_picture column to students table")
            else:
                print("ℹ️  profile_picture column already exists")
                
    except Exception as e:
        print(f"❌ Error adding column: {e}")

if __name__ == "__main__":
    add_profile_picture_column()
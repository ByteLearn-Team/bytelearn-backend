from database import engine
from sqlalchemy import text

def run():
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE students MODIFY COLUMN profile_picture LONGTEXT NULL;"))
        conn.commit()
    print("✅ profile_picture column changed to LONGTEXT")

if __name__ == "__main__":
    run()
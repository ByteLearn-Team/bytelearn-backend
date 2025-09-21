from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_USER = os.getenv("DB_USER", "avnadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "AVNS_HkMiEJ9UMnVe02fD5zD")
DB_HOST = os.getenv("DB_HOST", "mysql-1560ef6d-bytlearn077.i.aivencloud.com")
DB_PORT = os.getenv("DB_PORT", "16297")
DB_NAME = os.getenv("DB_NAME", "defaultdb")

DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl_verify_cert=false"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

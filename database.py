import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env so its values show up in os.getenv(...)
load_dotenv()

# 1. Read the five connection values from the environment
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))   # getenv returns a string; port needs an int
DB_NAME = os.getenv("DB_NAME")

# 2. Build the URL with URL.create — it percent-encodes special chars (the @ bug) for us
SQLALCHEMY_DATABASE_URL = URL.create(
    drivername="postgresql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

# 3. Engine — manages the connection pool to Postgres
engine = create_engine(SQLALCHEMY_DATABASE_URL)


# 4. Session maker + Base — unchanged
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
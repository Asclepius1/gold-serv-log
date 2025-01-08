import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.environ.get("HOST")

DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")

DATABASE_URL = os.environ.get("DATABASE_URL")
SECRET_KEY = os.environ.get("SECRET_KEY")

BEARER_TOKEN_GOLD_SERV = os.getenv("BEARER_TOKEN_GOLD_SERV")
GOLD_SERV_API_URL = os.getenv("GOLD_SERV_API_URL")

REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PASS = os.environ.get("REDIS_PASS")
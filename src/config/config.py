# src/config.py
import os

APPNAME = "Real-Time-Voice-AI-Interview-bot"
VERSION = "v1"
SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = "deepseek-v4-pro"  
    TEMPERATURE = 0.1     
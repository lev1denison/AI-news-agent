import os
from dotenv import load_dotenv

load_dotenv()
print("Tavily key loaded:", bool(os.getenv("TAVILY_API_KEY")))
print("Groq key loaded:", bool(os.getenv("GROQ_API_KEY")))
print("Resend key loaded:", bool(os.getenv("RESEND_API_KEY")))
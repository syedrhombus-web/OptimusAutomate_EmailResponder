import os
from dotenv import load_dotenv

load_dotenv()

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Email Processing Settings
MAX_EMAILS_TO_PROCESS = 10
CHECK_INTERVAL_SECONDS = 60
GMAIL_USER_ID = 'me'

# Email Categories
CATEGORIES = {
    'INQUIRY': 'inquiry',
    'COMPLAINT': 'complaint',
    'SUPPORT': 'support',
    'OTHER': 'other'
}
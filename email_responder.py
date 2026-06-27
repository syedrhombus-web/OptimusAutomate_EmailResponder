import os
import pickle
import base64
import time
from datetime import datetime
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from groq import Groq
import config

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.modify']

class AIEmailResponder:
    def __init__(self):
        """Initialize the email responder with Gmail API and Groq client"""
        self.gmail_service = self.authenticate_gmail()
        self.groq_client = Groq(api_key=config.GROQ_API_KEY)
        print("✅ AI Email Responder initialized successfully!")
    
    def authenticate_gmail(self):
        """Authenticate with Gmail API"""
        creds = None
        token_file = 'token.pickle'
        
        # Load existing credentials
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('gmail', 'v1', credentials=creds)
    
    def get_unread_emails(self, max_results=10):
        """Fetch unread emails from inbox"""
        try:
            result = self.gmail_service.users().messages().list(
                userId=config.GMAIL_USER_ID,
                labelIds=['INBOX'],
                q='is:unread',
                maxResults=max_results
            ).execute()
            
            messages = result.get('messages', [])
            emails = []
            
            for msg in messages:
                msg_data = self.gmail_service.users().messages().get(
                    userId=config.GMAIL_USER_ID,
                    id=msg['id']
                ).execute()
                
                email_info = self.extract_email_data(msg_data)
                if email_info:
                    emails.append(email_info)
            
            return emails
        
        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return []
    
    def extract_email_data(self, msg_data):
        """Extract relevant information from email"""
        try:
            payload = msg_data['payload']
            headers = payload.get('headers', [])
            
            # Extract headers
            subject = ''
            sender = ''
            for header in headers:
                if header['name'].lower() == 'subject':
                    subject = header['value']
                elif header['name'].lower() == 'from':
                    sender = header['value']
            
            # Extract body
            body = self.get_email_body(payload)
            
            return {
                'id': msg_data['id'],
                'sender': sender,
                'subject': subject,
                'body': body,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"❌ Error extracting email data: {e}")
            return None
    
    def get_email_body(self, payload):
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            # Multipart email
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            # Simple email
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body[:2000]  # Limit body length for processing
    
    def categorize_email(self, subject, body):
        """Categorize email using AI"""
        prompt = f"""
        Categorize the following email into one of these categories: 
        - INQUIRY: Questions, information requests
        - COMPLAINT: Complaints, negative feedback, issues
        - SUPPORT: Technical support, help requests
        - OTHER: Anything else

        Email Subject: {subject}
        Email Body: {body}

        Respond with ONLY the category name (INQUIRY, COMPLAINT, SUPPORT, or OTHER).
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are an email categorization expert. Respond with only the category name."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=20
            )
            
            category = response.choices[0].message.content.strip().upper()
            
            # Validate category
            valid_categories = ['INQUIRY', 'COMPLAINT', 'SUPPORT', 'OTHER']
            if category not in valid_categories:
                category = 'OTHER'
            
            return category
        
        except Exception as e:
            print(f"❌ Error categorizing email: {e}")
            return 'OTHER'
    
    def generate_reply(self, subject, body, category):
        """Generate AI-powered email reply"""
        templates = {
            'INQUIRY': "You are a helpful assistant responding to an inquiry. Be informative and friendly.",
            'COMPLAINT': "You are a professional customer service representative addressing a complaint. Be empathetic and solution-oriented.",
            'SUPPORT': "You are a technical support specialist helping with a problem. Be clear and solution-focused.",
            'OTHER': "You are a professional assistant responding to a general email. Be polite and helpful."
        }
        
        prompt = f"""
        Subject: {subject}
        Email: {body}
        Category: {category}

        Generate a professional email reply. Keep it concise (2-4 sentences).
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": templates.get(category, templates['OTHER'])},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"❌ Error generating reply: {e}")
            return "I have received your email and will get back to you shortly."
    
    def send_reply(self, email_data, reply_body):
        """Send reply email"""
        try:
            # Create email message
            message = MIMEText(reply_body)
            message['to'] = email_data['sender']
            message['subject'] = f"RE: {email_data['subject']}"
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send email
            self.gmail_service.users().messages().send(
                userId=config.GMAIL_USER_ID,
                body={'raw': raw_message}
            ).execute()
            
            print(f"✅ Reply sent to: {email_data['sender']}")
            return True
        
        except Exception as e:
            print(f"❌ Error sending reply: {e}")
            return False
    
    def mark_as_read(self, email_id):
        """Mark email as read"""
        try:
            self.gmail_service.users().messages().modify(
                userId=config.GMAIL_USER_ID,
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            print(f"✅ Email {email_id} marked as read")
            return True
        
        except Exception as e:
            print(f"❌ Error marking email as read: {e}")
            return False
    
    def process_emails(self):
        """Main processing loop"""
        print("\n📧 Checking for new emails...")
        emails = self.get_unread_emails(max_results=config.MAX_EMAILS_TO_PROCESS)
        
        if not emails:
            print("📭 No unread emails found.")
            return
        
        print(f"📬 Found {len(emails)} unread emails.\n")
        
        for idx, email_data in enumerate(emails, 1):
            print(f"\n{'='*50}")
            print(f"📨 Processing Email {idx}/{len(emails)}")
            print(f"From: {email_data['sender']}")
            print(f"Subject: {email_data['subject']}")
            print(f"{'='*50}")
            
            # Categorize email
            category = self.categorize_email(email_data['subject'], email_data['body'])
            print(f"🏷️  Category: {category}")
            
            # Generate reply
            reply = self.generate_reply(email_data['subject'], email_data['body'], category)
            print(f"🤖 Generated Reply:\n{reply}")
            
            # Send reply
            if self.send_reply(email_data, reply):
                # Mark as read after reply
                self.mark_as_read(email_data['id'])
                print(f"✅ Email {idx} processed successfully!")
            else:
                print(f"⚠️  Failed to process email {idx}")
    
    def run_continuously(self):
        """Run the email responder continuously"""
        print("🚀 Starting AI Email Responder...")
        print(f"⏰ Checking every {config.CHECK_INTERVAL_SECONDS} seconds\n")
        
        while True:
            try:
                self.process_emails()
                print(f"\n⏳ Waiting {config.CHECK_INTERVAL_SECONDS} seconds...\n")
                time.sleep(config.CHECK_INTERVAL_SECONDS)
            
            except KeyboardInterrupt:
                print("\n\n👋 Shutting down Email Responder...")
                break
            
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(30)

def main():
    """Main entry point"""
    responder = AIEmailResponder()
    
    # Process once
    responder.process_emails()
    
    # Uncomment below to run continuously
    #responder.run_continuously()

if __name__ == "__main__":
    main()
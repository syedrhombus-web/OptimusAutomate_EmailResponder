# 🤖 AI-Powered Email Responder

## Overview
Automated email responder using Gmail API and Groq LLM that reads emails, categorizes them, and generates intelligent replies.

## Features
- ✅ Read unread emails from Gmail
- 🏷️ AI-powered email categorization (Inquiry, Complaint, Support, Other)
- 🤖 Intelligent reply generation using Groq LLM
- 📤 Automatic reply sending
- 🔄 Mark emails as read after processing
- ⏰ Configurable check intervals

## Setup Instructions

### 1. Google Cloud Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download credentials as `credentials.json`

### 2. Install Dependencies
```bash
pip install -r requirements.txt
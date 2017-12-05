import os

DEBUG = False

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', None)
LOG_FILENAME = os.environ.get('LOG_FILENAME', 'app.log')

if not GOOGLE_API_KEY:
    raise ValueError("No google api key set for Flask application")

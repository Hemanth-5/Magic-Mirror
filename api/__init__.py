# This file makes the directory a Python package and exposes the Flask app
from flask import Flask

# Create Flask app instance
app = Flask(__name__)

# Import routes
from . import index

# This allows Vercel to import the app
# The app variable is what Vercel looks for when deploying
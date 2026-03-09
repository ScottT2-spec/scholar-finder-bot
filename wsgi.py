"""WSGI entry point for PythonAnywhere deployment"""
import sys
import os

# Add project directory to path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application

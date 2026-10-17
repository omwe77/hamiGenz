"""Pytest configuration for hamiGenZ backend tests.

Adds the backend directory to sys.path so test modules can import backend
packages directly (e.g. ``from main import app``).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
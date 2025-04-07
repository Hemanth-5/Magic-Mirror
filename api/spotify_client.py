"""
Spotify client state management.
This module provides a centralized way to manage the Spotify client instance.
"""
from spotipy import Spotify

# Global Spotify client instance
spotify_client = None

def get_client():
    """Get the current Spotify client instance."""
    global spotify_client
    return spotify_client

def set_client(client):
    """Set the Spotify client instance."""
    global spotify_client
    spotify_client = client

def is_initialized():
    """Check if the Spotify client is initialized."""
    global spotify_client
    return spotify_client is not None
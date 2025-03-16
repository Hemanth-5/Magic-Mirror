from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from collections import deque

# Configure Google AI
API_KEY = "AIzaSyCyAUf1hgB3K6abvs5fuC2kQCk_NZToU8w"
genai.configure(api_key=API_KEY)

# Configure Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Spotify API credentials
SPOTIFY_CLIENT_ID = "5b16824dcbf343059c84eb7ad962f790"
SPOTIFY_CLIENT_SECRET = "ba870b57e9bf49a085f750b482836ad8"
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"

# Initialize Spotipy client with authentication
sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-modify-playback-state user-read-playback-state user-read-currently-playing"
))

devices = sp.devices()
# Print the list of devices
print("Available Devices:")
# Extract the first available device ID
if devices.get("devices"):
    device_id = devices["devices"][0]["id"]
    print(f"\nYour Active Device ID: {device_id}")
else:
    print("\nNo active devices found. Please open Spotify and start playing music on a device.")
    


# Store the last 10 queries
message_history = deque(maxlen=10)

def control_music(command):
    """Control Spotify playback based on AI-generated commands."""
    try:
        if "play" in command:
            sp.start_playback()
            return "Playing music on Spotify."
        elif "pause" in command:
            sp.pause_playback()
            return "Music paused."
        elif "next" in command:
            sp.next_track()
            return "Skipped to the next song."
        elif "previous" in command:
            sp.previous_track()
            return "Playing the previous song."
        elif "what's playing" in command:
            current_track = sp.current_playback()
            if current_track and current_track["is_playing"]:
                song_name = current_track["item"]["name"]
                artist = current_track["item"]["artists"][0]["name"]
                return f"Now playing: {song_name} by {artist}."
            else:
                return "No music is currently playing."
        else:
            return "Sorry, I can't understand the command."
    except Exception as e:
        return f"Error controlling music: {e}"

def ask_google_assistant(prompt):
    """Process user query and return AI response or control music if applicable."""
    
    # Check if the query is music-related
    if any(word in prompt.lower() for word in ["play", "pause", "next", "previous", "what's playing"]):
        return control_music(prompt)

    # Process with Google AI for other queries
    model = genai.GenerativeModel("gemini-1.5-flash")
    try:
        response = model.generate_content(prompt)
        return response.text if response else "Sorry, I didn't understand."
    except Exception as e:
        return f"AI Error: {e}"

@app.route('/ask', methods=['POST'])
def ask():
    """API endpoint to get AI response."""
    data = request.get_json()
    if 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400

    user_query = data['query']
    print(f"Received query: {user_query}")

    # Get response from AI or control music
    response_text = ask_google_assistant(user_query)

    # Store query history
    message_history.append({'query': user_query, 'response': response_text})

    return jsonify({'response': response_text, 'history': list(message_history)})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

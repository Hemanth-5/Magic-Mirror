from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import google.generativeai as genai
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from collections import deque
import json
import re

# Configure Google AI
API_KEY = "AIzaSyCyAUf1hgB3K6abvs5fuC2kQCk_NZToU8w"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

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

# Fetch available devices
devices = sp.devices()
if devices.get("devices"):
    device_id = devices["devices"][0]["id"]
    print(f"\nYour Active Spotify Device ID: {device_id}")
else:
    print("\nNo active devices found. Please open Spotify and start playing music on a device.")

# Initialize deque to store the last 10 messages (query, response pairs)
message_history = deque(maxlen=10)

def get_gemini_response(prompt):
    """Get AI-generated response from Google Gemini."""
    try:
        response = model.generate_content(prompt)
        if not response or not response.text:
            return "{}"  # Return an empty JSON object to prevent errors
        print(f"Gemini Raw Response: {response.text}")  # Debugging
        return response.text
    except Exception as e:
        print(f"Error with Gemini AI: {e}")
        return "{}"  # Return empty JSON object


def extract_json_from_text(text):
    """Extract valid JSON from a text response."""
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    return "{}"  # Return empty JSON object if parsing fails

def extract_music_intent(user_query):
    """Determine if the command is music-related and extract relevant details."""
    prompt = f"""
    Analyze the following user query and determine whether it is related to music playback.

    - If it is a music command (play, pause, next, previous, song name, artist, etc.), return a structured JSON response with:
        - `intent`: (play, pause, next, previous, current_song)
        - `song_name`: (if mentioned, otherwise null)
        - `artist`: (if mentioned, otherwise null)

    - If the query is NOT about music, return `{{"intent": "general"}}`.

    User Query: "{user_query}"
    Return JSON format only.
    """
    response = get_gemini_response(prompt)
    json_response = extract_json_from_text(response)
    
    try:
        music_data = json.loads(json_response)
        print(f"Extracted Intent JSON: {music_data}")  # Debugging
        return music_data
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}, Response: {json_response}")  # Debugging
        return {"intent": "general"}  # Default to general if parsing fails
    
def control_music(user_query):
    """Control Spotify playback based on AI-detected intent."""
    music_data = extract_music_intent(user_query)
    print(f"Music Intent: {music_data}")  # Debugging


    try:
        if music_data["intent"] == "play":
            if music_data["song_name"]:
                query = f"{music_data['song_name']} {music_data['artist']}" if music_data.get("artist") else music_data["song_name"]
                results = sp.search(q=query, type='track', limit=1)
                
                if results["tracks"]["items"]:
                    track_uri = results["tracks"]["items"][0]["uri"]
                    track = results["tracks"]["items"][0]
                    sp.start_playback(uris=[track_uri])
                    return f"Playing {track['name']} by {track['artists'][0]['name']}."
                else:
                    return f"Sorry, I couldn't find {music_data['song_name']} on Spotify."
            else:
                sp.start_playback()
                return "Playing music on Spotify."
        
        elif music_data["intent"] == "pause":
            sp.pause_playback()
            return "Music paused."

        elif music_data["intent"] == "next":
            sp.next_track()
            return "Skipped to the next song."

        elif music_data["intent"] == "previous":
            sp.previous_track()
            return "Playing the previous song."

        elif music_data["intent"] == "current_song":
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
        print(f"Spotify API Error: {e}")  # Debugging
        return f"Error controlling music: {e}"

def ask_google_assistant(prompt):
    """Send a text query to Google Bard API or control music via Spotify."""
    
    # Check if the query is music-related
    if any(word in prompt.lower() for word in ["play", "pause", "next", "previous", "what's playing"]):
        return control_music(prompt)

    # Combine conversation history into a single string
    history_text = "\n".join([f"User: {msg['query']}\nAssistant: {msg['response']}" for msg in message_history])

    simplified_prompt = (
        "Imagine you are a magic mirror. You reflect the questions asked of you and offer answers in a clear, simple, and easy-to-understand way. "
        "Avoid using complex words, bullet points, or special characters. Keep your responses short and sweet, so they are easy for anyone to understand. "
        "You provide simple, natural answers as though you are a mirror reflecting the world around you. Don't make the answers too long or too short. "
        "Also, don't explicity say 'I am a mirror' or 'I reflect'. Just reflect the user's query in your response. "
        "When the reply is small, you can add a little more detail to make it more interesting. But not more than 1 sentence. "
        "Here is the conversation history:\n" + history_text + "\nUser's Question: " + prompt + "\nYour Response:"
    )


    try:
        response = model.generate_content(simplified_prompt)
        if response:
            return response.text
        else:
            return "The reflection is unclear... I cannot see the answer at this moment."
    except Exception as e:
        print(f"Error occurred: {e}")
        return "The mirror has clouded over... Please try again."

@app.route('/ask', methods=['POST'])
def ask():
    """API endpoint to process user queries - either control music or get an AI response."""
    data = request.get_json()
    if 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400

    user_query = data['query']
    print(f"Received query: {user_query}")

    # First, check if the query is related to music
    music_data = extract_music_intent(user_query)
    
    if music_data.get("intent") != "general":
        response_text = control_music(user_query)  # Directly handle music commands
    else:
        response_text = ask_google_assistant(user_query)  # Process through AI for general queries

    # Add the query and response to the message history
    message_history.append({'query': user_query, 'response': response_text})

    # Return the response
    return jsonify({'response': response_text, 'history': list(message_history)})


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
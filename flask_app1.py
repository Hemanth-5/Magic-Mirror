from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import spotipy 
from spotipy.oauth2 import SpotifyOAuth
import json
import re

# ----------------- GOOGLE GEMINI AI SETUP ----------------- #
API_KEY = "AIzaSyCyAUf1hgB3K6abvs5fuC2kQCk_NZToU8w"  # Replace with your actual API key
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ----------------- SPOTIFY API SETUP ----------------- #
SPOTIFY_CLIENT_ID = "5b16824dcbf343059c84eb7ad962f790"
SPOTIFY_CLIENT_SECRET = "ba870b57e9bf49a085f750b482836ad8"
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-modify-playback-state user-read-playback-state"
))

app = Flask(__name__)
CORS(app)  # Enable CORS

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

    if music_data.get("intent") == "general":
        return get_gemini_response(user_query)  # Regular AI response

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

@app.route('/ask', methods=['POST'])
def ask():
    """API endpoint to process user queries."""
    data = request.get_json()
    if 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400

    user_query = data['query']
    print(f"Received query: {user_query}")  # Debugging

    response_text = control_music(user_query)
    print(f"Response Sent: {response_text}")  # Debugging

    return jsonify({'response': response_text})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

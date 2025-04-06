from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import google.generativeai as genai
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from collections import deque
import json
import re
import datetime
import random
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Google AI
API_KEY = os.environ.get("GOOGLE_API_KEY", "")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Configure Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # For development only

# Spotify API credentials
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

# Initialize Spotipy client with authentication
sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-modify-playback-state user-read-playback-state user-read-currently-playing streaming"
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

# Global variable for active device
active_device_id = None

# Global variable for tracking conversation context
conversation_context = {
    'last_suggested_songs': [],
    'current_song_topic': None,
    'last_recommendation_query': None
}

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
    # Remove any triple backticks and "json" markers that might be in the response
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Try to find a JSON array or object
    json_match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
    if json_match:
        # Clean up the JSON string (remove excess whitespace and newlines)
        json_str = json_match.group(0)
        # Remove any trailing or leading whitespace on each line
        json_str = re.sub(r'^\s+|\s+$', '', json_str, flags=re.MULTILINE)
        return json_str
    
    return "{}"  # Return empty JSON object if parsing fails

def extract_music_intent(user_query):
    """Determine if the command is music-related and extract relevant details."""
    prompt = f"""
    Analyze the following user query and determine whether it is related to music playback.

    - If it is a music command (play, pause, next, previous, song name, artist, etc.), return a structured JSON response with:
        - `intent`: (play, pause, next, previous, current_song)
        - `song_name`: (if mentioned, otherwise null)
        - `artist`: (if mentioned, otherwise null)
        - `option_number`: (if user is selecting from options like "play option 1", extract the number)

    - If user is selecting from options (e.g., "play option 2", "choose option 1"), set:
        - `intent`: "play_option"
        - `option_number`: (the option number they selected, as an integer)

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

def analyze_mood_for_music(user_query):
    """Analyze user's query to determine mood and suggest appropriate music."""
    prompt = f"""
    Analyze the following statement and extract:
    1. The user's current mood or emotional state
    2. A music genre that would match this mood
    3. A specific search query for a song that would be appropriate
    
    Format your response as valid JSON with these fields:
    - mood: a brief description of the detected mood
    - genre: a music genre that matches the mood
    - song_query: a specific search phrase for Spotify (artist name and/or song title)
    
    User statement: "{user_query}"
    Return ONLY the JSON object without any additional text.
    """
    
    response = get_gemini_response(prompt)
    json_response = extract_json_from_text(response)
    
    try:
        mood_data = json.loads(json_response)
        print(f"Mood Analysis: {mood_data}")  # Debugging
        return mood_data
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error in mood analysis: {e}, Response: {json_response}")
        # Provide fallback values if parsing fails
        return {
            "mood": "neutral",
            "genre": "pop",
            "song_query": "popular hits"
        }

def play_on_active_device(uris=None, context_uri=None):
    """Play specified content on the active Spotify device."""
    global active_device_id
    
    try:
        # Get available devices if we don't have an active one or refresh anyway
        devices = sp.devices()
        available_devices = devices.get('devices', [])
        
        if not available_devices:
            print("⚠️ No available Spotify devices found. Please open Spotify on a device.")
            return False
            
        # Log all available devices
        print(f"Available Spotify devices: {len(available_devices)}")
        for i, device in enumerate(available_devices):
            print(f"  Device {i+1}: {device['name']} (ID: {device['id']}, Active: {device['is_active']})")
        
        # Prefer active devices, then the first available device
        active_devices = [d for d in available_devices if d.get('is_active')]
        
        if active_devices:
            # Use the currently active device
            active_device_id = active_devices[0]['id']
            print(f"Using currently active device: {active_devices[0]['name']} ({active_device_id})")
        else:
            # Use the first available device
            active_device_id = available_devices[0]['id']
            print(f"No active device, using first available: {available_devices[0]['name']} ({active_device_id})")
            
            # Try to activate this device
            try:
                sp.transfer_playback(device_id=active_device_id, force_play=False)
                print(f"Set {available_devices[0]['name']} as active device")
            except Exception as e:
                print(f"Note: Could not transfer playback (this is normal if no music is playing): {e}")
        
        # Prepare playback arguments
        play_kwargs = {'device_id': active_device_id}
        
        if uris:
            play_kwargs['uris'] = uris
            print(f"Starting playback with URIs: {uris}")
        elif context_uri:
            play_kwargs['context_uri'] = context_uri
            print(f"Starting playback with context URI: {context_uri}")
        
        # Attempt playback
        print("Calling start_playback with parameters:", play_kwargs)
        sp.start_playback(**play_kwargs)
        print("✅ Playback started successfully")
        return True
    
    except Exception as e:
        print(f"❌ Spotify playback error: {str(e)}")
        
        # Handle common errors
        if 'NO_ACTIVE_DEVICE' in str(e) or 'Device not found' in str(e):
            print("Trying to restart with a fresh device list...")
            try:
                # Force refresh devices
                devices = sp.devices()
                available_devices = devices.get('devices', [])
                
                if not available_devices:
                    print("Still no available devices after refresh")
                    return False
                
                # Select first device and force activation
                active_device_id = available_devices[0]['id']
                sp.transfer_playback(device_id=active_device_id, force_play=True)
                print(f"Transferred playback to {available_devices[0]['name']}")
                
                # Wait for device activation
                import time
                time.sleep(2)
                
                # Retry playback
                play_kwargs = {'device_id': active_device_id}
                if uris:
                    play_kwargs['uris'] = uris
                elif context_uri:
                    play_kwargs['context_uri'] = context_uri
                
                sp.start_playback(**play_kwargs)
                print("✅ Playback started successfully after retry")
                return True
            except Exception as retry_error:
                print(f"Failed after retry: {retry_error}")
                return False
                
        # Premium account issues
        elif 'PREMIUM_REQUIRED' in str(e):
            print("This operation requires a Spotify Premium account")
            return False
            
        return False

def control_music(user_query):
    """Control Spotify playback based on AI-detected intent."""
    music_data = extract_music_intent(user_query)
    print(f"Music Intent: {music_data}")  # Debugging

    try:
        if music_data["intent"] == "play":
            if music_data.get("song_name"):
                # Safely get song_name and artist, ensuring they're strings
                song_name = music_data.get("song_name", "").lower() if music_data.get("song_name") else ""
                artist = music_data.get("artist", "").lower() if music_data.get("artist") else ""
                
                # Construct search query
                query = f"{song_name} {artist}".strip()
                
                # Search for tracks with the given query
                results = sp.search(q=query, type='track', limit=3)
                
                if results["tracks"]["items"]:
                    tracks = results["tracks"]["items"]
                    
                    # Check for exact match (case insensitive)
                    exact_match = None
                    for track in tracks:
                        track_name = track["name"].lower()
                        track_artist = track["artists"][0]["name"].lower() if track["artists"] else ""
                        
                        # Check if this is an exact match
                        name_match = song_name in track_name or track_name in song_name
                        artist_match = not artist or artist in track_artist or track_artist in artist
                        
                        if name_match and artist_match:
                            exact_match = track
                            break
                    
                    # If we found an exact match, play it
                    if exact_match:
                        success = play_on_active_device(uris=[exact_match["uri"]])
                        if success:
                            return f"Playing {exact_match['name']} by {exact_match['artists'][0]['name']}."
                        else:
                            return "I found the song but couldn't play it. Please make sure Spotify is open on your device."
                    
                    # Otherwise, offer the top 3 options
                    options = []
                    for i, track in enumerate(tracks, 1):
                        artist_name = track["artists"][0]["name"] if track["artists"] else "Unknown Artist"
                        options.append(f"{i}. {track['name']} by {artist_name}")
                    
                    options_text = "\n".join(options)
                    return f"I found these songs matching your request:\n{options_text}\nPlease say 'play option 1', 'play option 2', or 'play option 3' to select one, or try a more specific search."
                else:
                    return f"Sorry, I couldn't find {music_data['song_name']} on Spotify."
            else:
                # Check if this is a mood-based request for music
                if any(phrase in user_query.lower() for phrase in [
                    "play a song", "play some music", "feeling", "mood", "play something", 
                    "i want to listen", "let's listen", "how about some music"
                ]):
                    # This appears to be a mood-based music request
                    mood_data = analyze_mood_for_music(user_query)
                    
                    # Search for a song based on the AI's suggestion
                    results = sp.search(q=mood_data["song_query"], type='track', limit=1)
                    
                    if results["tracks"]["items"]:
                        track = results["tracks"]["items"][0]
                        success = play_on_active_device(uris=[track["uri"]])
                        if success:
                            return f"Based on your mood ({mood_data['mood']}), I'm playing {track['name']} by {track['artists'][0]['name']}. Enjoy!"
                        else:
                            return "I found a song for your mood but couldn't play it. Please make sure Spotify is open."
                    else:
                        # Fallback to genre search if specific song search fails
                        genre_results = sp.search(q=mood_data["genre"], type='track', limit=1)
                        if genre_results["tracks"]["items"]:
                            track = genre_results["tracks"]["items"][0]
                            success = play_on_active_device(uris=[track["uri"]])
                            if success:
                                return f"I found some {mood_data['genre']} music for your {mood_data['mood']} mood. Playing {track['name']} by {track['artists'][0]['name']}."
                            else:
                                return "I found some music but couldn't play it. Please make sure Spotify is open."
                        else:
                            # Just play any music as last resort
                            success = play_on_active_device()
                            if success:
                                return "Playing some music for you. I hope you enjoy it!"
                            else:
                                return "I tried to play some music but couldn't. Please make sure Spotify is open."
                else:
                    # Just a general "play" command
                    success = play_on_active_device()
                    if success:
                        return "Playing music on Spotify."
                    else:
                        return "I couldn't play music. Please make sure Spotify is open on your device."
        
        elif music_data["intent"] == "play_option":
            # Handle selection from previous options
            option_number = music_data.get("option_number")
            
            # Check if option number is valid
            if option_number is not None:
                # Convert from 1-based (user perspective) to 0-based (array index)
                option_index = option_number - 1
                
                # Make sure it's in range
                if option_index >= 0 and option_index < len(conversation_context.get('last_suggested_songs', [])):
                    return play_suggested_song(option_index)
                else:
                    print(f"Option number {option_number} (index {option_index}) out of range")
            
            # Check if user wants to play any suggestion
            if option_number is None and conversation_context['last_suggested_songs']:
                any_option_phrases = [
                    "any", "anyone", "any one", "any of them", "random", 
                    "whatever", "any song", "any option", "one of them"
                ]
                
                is_any_option = any(phrase in user_query.lower() for phrase in any_option_phrases)
                
                if is_any_option:
                    # Play a random suggestion from the list
                    import random
                    option_index = random.randint(0, len(conversation_context['last_suggested_songs']) - 1)
                    return play_suggested_song(option_index)
                
                # If no specific option requested, default to first
                return play_suggested_song(0)
                
            return "Sorry, I couldn't find that option. Please try your search again."
        
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
        return "Error controlling music. Please try again."

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

def get_similar_songs(song_name, artist=None, limit=5):
    """Get similar songs to a given track using Spotify recommendations."""
    try:
        # First search for the seed track
        query = f"track:{song_name}"
        if artist:
            query += f" artist:{artist}"
        
        results = sp.search(q=query, type='track', limit=1)
        
        if not results['tracks']['items']:
            # If no exact match, try a more general search
            query = song_name
            if artist:
                query += f" {artist}"
            results = sp.search(q=query, type='track', limit=1)
        
        if results['tracks']['items']:
            seed_track = results['tracks']['items'][0]
            
            try:
                # First try: Get recommendations using seed track
                recommendations = sp.recommendations(
                    seed_tracks=[seed_track['id']], 
                    limit=limit
                )
                
                recommended_tracks = []
                for track in recommendations['tracks']:
                    recommended_tracks.append({
                        'name': track['name'],
                        'artist': track['artists'][0]['name'],
                        'uri': track['uri'],
                        'id': track['id']
                    })
                
                if recommended_tracks:
                    print(f"Found {len(recommended_tracks)} recommendations using seed track")
                    return recommended_tracks
                    
            except Exception as rec_error:
                print(f"Error with recommendations API: {rec_error}")
                # Using AI to generate recommendations instead of manual fallback methods
                return get_ai_fallback_recommendations(seed_track, limit)
    
    except Exception as e:
        print(f"Error getting song recommendations: {e}")
        return []

def get_ai_fallback_recommendations(seed_track, limit=5):
    """Use AI to generate fallback recommendations when Spotify API methods fail."""
    try:
        # Extract information about the seed track
        song_name = seed_track['name']
        artist_name = seed_track['artists'][0]['name']
        
        # Create a prompt for Gemini to suggest similar songs
        prompt = f"""
        I need recommendations for songs similar to "{song_name}" by {artist_name}.
        Please suggest {limit} songs that are musically similar or related.
        
        Return your response as a JSON array with this format:
        [
            {{"name": "Song Name 1", "artist": "Artist Name 1"}},
            {{"name": "Song Name 2", "artist": "Artist Name 2"}},
            ...
        ]
        
        Only return the JSON array, nothing else.
        """
        
        # Get recommendations from Gemini
        response = get_gemini_response(prompt)
        json_response = extract_json_from_text(response)
        
        try:
            recommended_songs = json.loads(json_response)
            
            if isinstance(recommended_songs, list) and recommended_songs:
                # For each AI-suggested song, search Spotify to get the URI
                ai_recommended_tracks = []
                
                for song in recommended_songs[:limit]:
                    if 'name' in song and 'artist' in song:
                        # Search Spotify for this song
                        search_query = f"{song['name']} {song['artist']}"
                        results = sp.search(q=search_query, type='track', limit=1)
                        
                        if results['tracks']['items']:
                            track = results['tracks']['items'][0]
                            ai_recommended_tracks.append({
                                'name': track['name'],
                                'artist': track['artists'][0]['name'],
                                'uri': track['uri'],
                                'id': track['id']
                            })
                
                if ai_recommended_tracks:
                    print(f"Found {len(ai_recommended_tracks)} recommendations using AI fallback")
                    return ai_recommended_tracks
        except json.JSONDecodeError as json_err:
            print(f"Error decoding AI recommendations JSON: {json_err}")
        
        # If AI recommendations failed or returned no valid results, try artist fallback
        print("Trying artist fallback after AI recommendations failed")
        artist_id = seed_track['artists'][0]['id']
            
        try:
            # Get top tracks from the same artist
            artist_tracks = sp.artist_top_tracks(artist_id)
            
            recommended_tracks = []
            for track in artist_tracks['tracks'][:limit]:
                # Skip the original song
                if track['id'] == seed_track['id']:
                    continue
                        
                recommended_tracks.append({
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'uri': track['uri'],
                    'id': track['id']
                })
            
            if recommended_tracks:
                print(f"Found {len(recommended_tracks)} recommendations using artist top tracks")
                return recommended_tracks
                    
        except Exception as artist_error:
            print(f"Error getting artist top tracks: {artist_error}")
        
        # If all else fails, search for related terms
        search_term = f"{seed_track['artists'][0]['name']} similar"
        similar_results = sp.search(q=search_term, type='track', limit=limit)
        
        recommended_tracks = []
        for track in similar_results['tracks']['items']:
            # Skip the original song
            if track['id'] == seed_track['id']:
                continue
                    
            recommended_tracks.append({
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'uri': track['uri'],
                'id': track['id']
            })
        
        print(f"Found {len(recommended_tracks)} recommendations using search")
        return recommended_tracks
    except Exception as e:
        print(f"Error getting song recommendations: {e}")
        return []

def get_genre_recommendations(genre, limit=5):
    """Get song recommendations for a specific genre."""
    try:
        print(f"Searching for genre: {genre}")
        
        # First try searching directly with the genre
        results = sp.search(q=genre, type='track', limit=limit)
        
        if not results['tracks']['items']:
            # Try variations of the genre name
            alternative_queries = [
                f"best {genre}", 
                f"{genre} top", 
                f"{genre} hits",
                f"popular {genre}"
            ]
            
            for query in alternative_queries:
                results = sp.search(q=query, type='track', limit=limit)
                if results['tracks']['items']:
                    print(f"Found results with query: {query}")
                    break
        
        recommended_tracks = []
        for track in results['tracks']['items']:
            recommended_tracks.append({
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'uri': track['uri'],
                'id': track['id']
            })
        
        print(f"Found {len(recommended_tracks)} tracks for genre: {genre}")
        return recommended_tracks
    
    except Exception as e:
        print(f"Error getting genre recommendations: {e}")
        return []

def get_song_suggestions():
    """Get song suggestions based on conversation context using AI."""
    global conversation_context
    
    # Create an AI prompt based on the current context
    query_context = ""
    
    if conversation_context.get('current_song_topic'):
        query_context += f" similar to {conversation_context['current_song_topic']}"
    
    if conversation_context.get('artist'):
        query_context += f" by or similar to {conversation_context['artist']}"
    
    if conversation_context.get('genre'):
        query_context += f" in the {conversation_context['genre']} genre"
    
    if conversation_context.get('mood'):
        query_context += f" that match the mood: {conversation_context['mood']}"
    
    # If no context, use the original query
    if not query_context and conversation_context.get('last_recommendation_query'):
        query_context = conversation_context['last_recommendation_query']
    
    # Use AI to determine the best songs for this request
    prompt = f"""
    As a music expert, recommend 5 songs {query_context}.
    
    Be very specific about understanding the user's mood and intent:
    - If they mentioned a date or romantic situation, suggest romantic or upbeat love songs
    - If they mentioned needing confidence, suggest empowering songs
    - If they mentioned relaxing, suggest calming songs
    - Always prioritize popular, well-known songs that match the mood over obscure tracks
    
    Return your response ONLY as a JSON array with this format:
    [
        {{"name": "Song Name 1", "artist": "Artist Name 1"}},
        {{"name": "Song Name 2", "artist": "Artist Name 2"}},
        {{"name": "Song Name 3", "artist": "Artist Name 3"}},
        {{"name": "Song Name 4", "artist": "Artist Name 4"}},
        {{"name": "Song Name 5", "artist": "Artist Name 5"}}
    ]
    """
    
    response = get_gemini_response(prompt)
    json_response = extract_json_from_text(response)
    
    try:
        ai_suggestions = json.loads(json_response)
        
        if isinstance(ai_suggestions, list) and ai_suggestions:
            # Convert AI suggestions to actual Spotify tracks
            recommendations = []
            
            for song in ai_suggestions[:5]:
                if 'name' in song and 'artist' in song:
                    # Search Spotify for this song
                    search_query = f"{song['name']} {song['artist']}"
                    results = sp.search(q=search_query, type='track', limit=1)
                    
                    if results['tracks']['items']:
                        track = results['tracks']['items'][0]
                        recommendations.append({
                            'name': track['name'],
                            'artist': track['artists'][0]['name'],
                            'uri': track['uri'],
                            'id': track['id']
                        })
            
            if recommendations:
                # Store the recommendations
                conversation_context['last_suggested_songs'] = recommendations
                
                # Format the response
                suggestion_text = f"Based on your mood, here are some songs that might help:\n"
                for i, track in enumerate(recommendations[:3], 1):
                    suggestion_text += f"{i}. \"{track['name']}\" by {track['artist']}\n"
                
                suggestion_text += "\nWould you like me to play any of these?"
                return suggestion_text
    except json.JSONDecodeError as json_err:
        print(f"Error decoding AI song suggestions: {json_err}")
    
    # Fallback - use AI for a general mood-based recommendation
    return ai_mood_based_fallback()

def analyze_music_suggestion_request(user_query):
    """Check if the user is asking for song suggestions."""
    prompt = f"""
    Determine if the user is asking for music or song suggestions/recommendations.
    If they are, extract the type of music they're interested in.
    
    Return JSON with:
    - "is_asking_for_suggestions": true/false 
    - "reference_song": song name they mentioned (or null)
    - "reference_artist": artist they mentioned (or null)
    - "genre": genre they're interested in (or null)
    - "mood": mood they're interested in (or null)

    Examples:
    "suggest me some songs like Shape of You" -> {{"is_asking_for_suggestions": true, "reference_song": "Shape of You", "reference_artist": null, "genre": null, "mood": null}}
    "play something like Ed Sheeran" -> {{"is_asking_for_suggestions": true, "reference_song": null, "reference_artist": "Ed Sheeran", "genre": null, "mood": null}}
    "recommend some upbeat songs" -> {{"is_asking_for_suggestions": true, "reference_song": null, "reference_artist": null, "genre": null, "mood": "upbeat"}}
    "anime songs?" -> {{"is_asking_for_suggestions": true, "reference_song": null, "reference_artist": null, "genre": "anime", "mood": null}}
    "what's the weather like" -> {{"is_asking_for_suggestions": false, "reference_song": null, "reference_artist": null, "genre": null, "mood": null}}
    
    User query: "{user_query}"
    Return only JSON format.
    """
    
    response = get_gemini_response(prompt)
    json_response = extract_json_from_text(response)
    
    try:
        suggestion_data = json.loads(json_response)
        print(f"Suggestion Analysis: {suggestion_data}")  # Debugging
        return suggestion_data
    except json.JSONDecodeError:
        return {"is_asking_for_suggestions": False}

def play_suggested_song(index=0):
    """Play a suggested song by index."""
    global conversation_context
    
    suggested_songs = conversation_context.get('last_suggested_songs', [])
    
    if not suggested_songs:
        return "I don't have any suggested songs to play right now."
    
    # Ensure the index is within bounds
    if index >= len(suggested_songs):
        print(f"Requested song index {index} is out of bounds (max: {len(suggested_songs)-1})")
        index = 0
    
    # Get the selected song
    selected_song = suggested_songs[index]
    print(f"Playing suggested song at index {index}: {selected_song['name']} by {selected_song['artist']}")
    
    # Play the song
    success = play_on_active_device(uris=[selected_song['uri']])
    if success:
        return f"Playing \"{selected_song['name']}\" by {selected_song['artist']}."
    else:
        return "I couldn't play the suggested song. Please make sure Spotify is open."

def process_play_request(user_query):
    """Process a 'play' request, checking for references to suggested songs."""
    global conversation_context
    music_data = extract_music_intent(user_query)
    
    # Check for references to "it" or "that song" when we have suggestions
    if not music_data.get("song_name") and conversation_context['last_suggested_songs']:
        references_suggestion = any(phrase in user_query.lower() for phrase in [
            "it", "that", "this", "the song", "that song", "this song", "the one", "that one"
        ])
        
        if references_suggestion:
            print("Detected reference to a previously suggested song")
            return play_suggested_song(0)  # Play the first suggested song
            
        # Check for option selection (e.g., "play the first one", "play #2")
        option_match = re.search(r"(?:play|choose)(?:\s+the)?\s+(\w+)(?:\s+one)?", user_query.lower())
        if option_match:
            option_word = option_match.group(1)
            option_index = -1
            
            # Convert words to numbers
            if option_word == "first" or option_word == "1" or option_word == "#1": 
                option_index = 0
            elif option_word == "second" or option_word == "2" or option_word == "#2": 
                option_index = 1
            elif option_word == "third" or option_word == "3" or option_word == "#3":
                option_index = 2
                
            if option_index >= 0:
                print(f"Detected selection of suggestion #{option_index + 1}")
                return play_suggested_song(option_index)
    
    # Proceed with regular play logic if no suggestion reference was detected
    return control_music(user_query)

def analyze_music_request(user_query):
    """Use AI to comprehensively analyze a music-related request."""
    prompt = f"""
    Analyze this music-related request: "{user_query}"
    
    Return a detailed JSON with the following information:
    
    1. Top-level intent (determine the primary goal):
       - "play": User wants to play a specific song/artist directly
       - "suggest": User wants recommendations or suggestions
       - "control": User wants to control playback (pause, next, etc.)
       - "query": User is asking about music information
    
    2. Details based on intent:
       - For "play": Include song_name, artist, specific_request_type (exact_song, artist_songs, playlist)
       - For "suggest": Include reference_song, reference_artist, genre, mood
       - For "control": Include action (pause, next, previous, resume, volume)
       - For "query": Include question_type (current_song, artist_info, lyrics)
    
    3. Option selection (if applicable):
       - option_number: If user is selecting from a numbered list (e.g. "play the third one")
       - is_selecting_option: true/false for if this is an option selection
    
    Example responses:
    - For "play Katchi by Ofenbach": {{\"intent\":\"play\", \"song_name\":\"Katchi\", \"artist\":\"Ofenbach\", \"specific_request_type\":\"exact_song\", \"is_selecting_option\":false}}
    - For "suggest songs like Katchi": {{\"intent\":\"suggest\", \"reference_song\":\"Katchi\", \"reference_artist\":null, \"genre\":null, \"mood\":null, \"is_selecting_option\":false}}
    - For "play the third option": {{\"intent\":\"play\", \"is_selecting_option\":true, \"option_number\":3}}
    - For "next song": {{\"intent\":\"control\", \"action\":\"next\"}}
    
    Analyze carefully to distinguish between requests to play specific songs vs requests for suggestions/recommendations.
    """
    
    response = get_gemini_response(prompt)
    json_response = extract_json_from_text(response)
    
    try:
        request_data = json.loads(json_response)
        print(f"AI Request Analysis: {request_data}")  # Debugging
        return request_data
    except json.JSONDecodeError as e:
        print(f"Error decoding AI analysis: {e}")
        return {"intent": "unknown"}

def analyze_request_intent(user_query):
    """Use AI to analyze user requests and determine if they're music-related or general questions."""
    prompt = f"""
    Analyze this user request: "{user_query}"
    
    Determine if this is a music-related request or a general question.
    
    Return a detailed JSON with the following information:
    
    1. Top-level intent:
       - "music": User wants to play music, get music recommendations, or control music playback
       - "general": User is asking a general question not related to music
    
    2. If intent is "music", include these details:
       - "sub_intent": One of "play", "suggest", "control", or "query"
       - For "play": Include song_name, artist, specific_request_type (exact_song, artist_songs, playlist)
       - For "suggest": Include reference_song, reference_artist, genre, mood
       - For "control": Include action (pause, next, previous, resume, volume)
       - For "query": Include question_type (current_song, artist_info, lyrics)
       - If the user is selecting from options: is_selecting_option (true/false), option_number (if applicable)
    
    3. If intent is "general", include these details:
       - "query_type": "factual", "conversational", "personal", "greeting", or "other"
    
    Example responses:
    - For "play Katchi by Ofenbach": {{\"intent\":\"music\", \"sub_intent\":\"play\", \"song_name\":\"Katchi\", \"artist\":\"Ofenbach\", \"specific_request_type\":\"exact_song\", \"is_selecting_option\":false}}
    - For "what's the weather today": {{\"intent\":\"general\", \"query_type\":\"factual\"}}
    - For "how are you doing": {{\"intent\":\"general\", \"query_type\":\"greeting\"}}
    - For "play the third option": {{\"intent\":\"music\", \"sub_intent\":\"play\", \"is_selecting_option\":true, \"option_number\":3}}
    
    Analyze carefully to determine if this is a music request or a general query.
    """
    
    response = get_gemini_response(prompt)
    json_response = extract_json_from_text(response)
    
    try:
        request_data = json.loads(json_response)
        print(f"AI Request Analysis: {request_data}")  # Debugging
        return request_data
    except json.JSONDecodeError as e:
        print(f"Error decoding AI analysis: {e}")
        return {"intent": "general"}  # Default to general if parsing fails

@app.route('/ask', methods=['POST'])
def ask():
    """API endpoint to process user queries with AI-driven intent recognition."""
    global conversation_context
    
    data = request.get_json()
    if 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400

    user_query = data['query']
    print(f"Received query: {user_query}")
    
    # Use AI to analyze whether this is a music request or general question
    request_analysis = analyze_request_intent(user_query)
    intent = request_analysis.get("intent", "general")
    
    # Handle different types of intents
    if intent == "music":
        sub_intent = request_analysis.get("sub_intent", "unknown")
        
        if sub_intent == "play":
            if request_analysis.get("is_selecting_option", False):
                # User is selecting from previously suggested options
                option_number = request_analysis.get("option_number", 1)
                # Convert to zero-based index
                option_index = option_number - 1
                response_text = play_suggested_song(option_index)
                
            elif request_analysis.get("song_name"):
                # User wants to play a specific song
                song_name = request_analysis.get("song_name")
                artist = request_analysis.get("artist")
                
                # Search Spotify for the song
                query = f"{song_name}"
                if artist:
                    query += f" {artist}"
                    
                results = sp.search(q=query, type='track', limit=3)
                
                if results["tracks"]["items"]:
                    tracks = results["tracks"]["items"]
                    
                    # If we found exactly one match or an exact match, play it directly
                    if len(tracks) == 1 or (song_name.lower() in tracks[0]["name"].lower()):
                        track = tracks[0]
                        success = play_on_active_device(uris=[track["uri"]])
                        if success:
                            response_text = f"Playing \"{track['name']}\" by {track['artists'][0]['name']}."
                        else:
                            response_text = "I found the song but couldn't play it. Please make sure Spotify is open."
                    else:
                        # Store the tracks as options
                        conversation_context['last_suggested_songs'] = [
                            {
                                'name': track['name'],
                                'artist': track['artists'][0]['name'],
                                'uri': track['uri'],
                                'id': track['id']
                            }
                            for track in tracks
                        ]
                        
                        # Format options for display
                        options_text = "I found these songs matching your request:\n"
                        for i, track in enumerate(tracks, 1):
                            options_text += f"{i}. \"{track['name']}\" by {track['artists'][0]['name']}\n"
                        
                        options_text += "\nWhich one would you like me to play?"
                        response_text = options_text
                else:
                    response_text = f"Sorry, I couldn't find a song matching \"{song_name}\" on Spotify."
            else:
                # Generic play request without specific song
                # Check if we should use the last suggested songs
                if conversation_context.get('last_suggested_songs'):
                    response_text = play_suggested_song(0)  # Play first suggested
                else:
                    response_text = "I'm not sure which song you'd like me to play. Could you specify a song or artist?"
        
        elif sub_intent == "suggest":
            # Update conversation context with suggestion details
            if request_analysis.get("reference_song"):
                conversation_context['current_song_topic'] = request_analysis["reference_song"]
            if request_analysis.get("reference_artist"):
                conversation_context['artist'] = request_analysis["reference_artist"]
            if request_analysis.get("genre"):
                conversation_context['genre'] = request_analysis["genre"]
            if request_analysis.get("mood"):
                conversation_context['mood'] = request_analysis["mood"]
                
            conversation_context['last_recommendation_query'] = user_query
            
            # Get AI-driven song suggestions
            response_text = get_song_suggestions()
        
        elif sub_intent == "control":
            # Process playback control commands
            action = request_analysis.get("action", "")
            
            try:
                if action == "pause":
                    sp.pause_playback()
                    response_text = "Music paused."
                elif action == "resume" or action == "play":
                    sp.start_playback()
                    response_text = "Resuming playback."
                elif action == "next":
                    sp.next_track()
                    response_text = "Skipped to the next song."
                elif action == "previous":
                    sp.previous_track()
                    response_text = "Playing the previous song."
                elif action == "volume":
                    # Future enhancement: handle volume control
                    response_text = "I'm sorry, volume control is not yet implemented."
                else:
                    response_text = "I'm not sure how to control the playback with that command."
            except Exception as e:
                print(f"Error controlling playback: {e}")
                response_text = "I couldn't control the playback. Please make sure Spotify is open and playing."
        
        elif sub_intent == "query":
            # Handle music information queries
            query_type = request_analysis.get("question_type", "")
            
            if query_type == "current_song":
                current_track = sp.current_playback()
                if current_track and current_track.get("item"):
                    song_name = current_track["item"]["name"]
                    artist = current_track["item"]["artists"][0]["name"]
                    response_text = f"Now playing: {song_name} by {artist}."
                else:
                    response_text = "No music is currently playing."
            else:
                # For other music query types, get AI to generate a response
                response_text = get_ai_response_for_music_query(user_query)
    
    else:  # intent == "general" or any other case
        # This is a general query, use the Google Assistant for a response
        response_text = ask_google_assistant(user_query)
    
    # Add the query and response to the message history
    message_history.append({'query': user_query, 'response': response_text})

    # Return the response
    return jsonify({'response': response_text, 'history': list(message_history)})

# Add these new endpoints

@app.route('/get-spotify-token', methods=['GET'])
def get_spotify_token():
    """Return the current Spotify OAuth token to the frontend."""
    try:
        # Get the current token from SpotifyOAuth
        token_info = sp.auth_manager.get_cached_token()
        if token_info and 'access_token' in token_info:
            return jsonify({'token': token_info['access_token']})
        return jsonify({'error': 'No token available'}), 400
    except Exception as e:
        print(f"Error retrieving Spotify token: {e}")
        return jsonify({'error': 'Failed to retrieve token'}), 500

@app.route('/set-active-device', methods=['POST'])
def set_active_device():
    """Set the active Spotify device ID."""
    global active_device_id
    
    data = request.get_json()
    if 'device_id' not in data:
        return jsonify({'error': 'device_id is required'}), 400
    
    active_device_id = data['device_id']
    print(f"Set active Spotify device ID to: {active_device_id}")
    
    # Try to transfer playback to this device
    try:
        sp.transfer_playback(device_id=active_device_id, force_play=False)
        print(f"Successfully transferred playback to device: {active_device_id}")
    except Exception as e:
        print(f"Note: Could not transfer playback (this is normal if no music is playing): {e}")
    
    return jsonify({'success': True})

@app.route('/api/data', methods=['GET'])
def get_data():
    """API endpoint to provide general data for the mirror display."""
    current_time = datetime.datetime.now()
    
    # Get current weather (mock data for now)
    weather_conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear"]
    temperatures = list(range(15, 30))  # Temperature range in Celsius
    
    weather = {
        "condition": random.choice(weather_conditions),
        "temperature": random.choice(temperatures),
        "humidity": random.randint(30, 90)
    }
    
    # Format time
    formatted_time = current_time.strftime("%H:%M:%S")
    
    # Return the data
    return jsonify({
        "time": formatted_time,
        "date": current_time.strftime("%Y-%m-%d"),
        "weather": f"{weather['condition']} {weather['temperature']}°C",
        "humidity": f"{weather['humidity']}%",
        "updated_at": current_time.isoformat()
    })

def ai_mood_based_fallback():
    """Use AI to generate song recommendations based on current conversation context when other methods fail."""
    global conversation_context
    
    # Use the last query directly for better context
    query = conversation_context.get('last_recommendation_query', '')
    
    # Create a detailed AI prompt to get mood-appropriate songs
    prompt = f"""
    As a music expert, I need song recommendations for this request:
    "{query}"
    
    Please analyze the request and recommend 5 songs that would be perfect for this situation.
    Consider the mood, activity, situation, and any implied emotions in the request.
    
    Pay special attention to:
    1. If they mentioned a date, romantic outing, or love - suggest popular romantic songs
    2. If they want a confidence boost - suggest empowering, upbeat songs
    3. If they want to relax or calm down - suggest soothing, peaceful songs
    4. If they're feeling sad - suggest uplifting or comforting songs
    5. If they mentioned a specific activity - suggest songs that pair well with that activity
    
    Return your suggestions ONLY as a JSON array with this format:
    [
        {{"name": "Song Name 1", "artist": "Artist Name 1"}},
        {{"name": "Song Name 2", "artist": "Artist Name 2"}},
        {{"name": "Song Name 3", "artist": "Artist Name 3"}},
        {{"name": "Song Name 4", "artist": "Artist Name 4"}},
        {{"name": "Song Name 5", "artist": "Artist Name 5"}}
    ]
    """
    
    # Get AI recommendations
    response = get_gemini_response(prompt)
    json_response = extract_json_from_text(response)
    
    try:
        ai_suggestions = json.loads(json_response)
        
        if isinstance(ai_suggestions, list) and ai_suggestions:
            # Convert AI suggestions to actual Spotify tracks
            recommendations = []
            
            for song in ai_suggestions[:5]:
                if 'name' in song and 'artist' in song:
                    # Search Spotify for this song
                    search_query = f"{song['name']} {song['artist']}"
                    results = sp.search(q=search_query, type='track', limit=1)
                    
                    if results['tracks']['items']:
                        track = results['tracks']['items'][0]
                        recommendations.append({
                            'name': track['name'],
                            'artist': track['artists'][0]['name'],
                            'uri': track['uri'],
                            'id': track['id']
                        })
            
            if recommendations:
                # Store the recommendations
                conversation_context['last_suggested_songs'] = recommendations
                
                # Format the response
                suggestion_text = f"For your mood, here are some songs you might enjoy:\n"
                for i, track in enumerate(recommendations[:3], 1):
                    suggestion_text += f"{i}. \"{track['name']}\" by {track['artist']}\n"
                
                suggestion_text += "\nWould you like me to play any of these?"
                return suggestion_text
    except json.JSONDecodeError as json_err:
        print(f"Error decoding AI mood fallback suggestions: {json_err}")
    
    # Ultimate fallback - generic message with a random song
    try:
        # Search for a random popular song
        results = sp.search(q="top hits", type='track', limit=3)
        if results['tracks']['items']:
            tracks = results['tracks']['items']
            conversation_context['last_suggested_songs'] = [
                {
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'uri': track['uri'],
                    'id': track['id']
                }
                for track in tracks
            ]
            
            suggestion_text = "I found some songs that might lift your mood:\n"
            for i, track in enumerate(tracks, 1):
                suggestion_text += f"{i}. \"{track['name']}\" by {track['artists'][0]['name']}\n"
            
            suggestion_text += "\nWould you like me to play any of these?"
            return suggestion_text
    except Exception as e:
        print(f"Error in final fallback: {e}")
        
    return "I couldn't find specific songs for your mood. Would you like me to play something popular instead?"

def get_ai_response_for_music_query(user_query):
    """Generate AI responses for music-related information queries."""
    prompt = f"""
    As a music expert, please answer this music-related question:
    "{user_query}"
    
    Keep your answer concise, helpful, and focused on the music topic.
    If the question is about song lyrics, artist information, music history, 
    or other music topics, provide accurate information.
    
    If you're not sure about the exact answer, it's better to say so
    rather than providing potentially incorrect information.
    """
    
    response = get_gemini_response(prompt)
    return response

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
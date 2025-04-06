from http.server import BaseHTTPRequestHandler
import json
import datetime
import google.generativeai as genai
import os
import random

# Configure Google AI
API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()
        
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()
        
        # Handle API data endpoint
        if self.path.startswith('/api/data'):
            current_time = datetime.datetime.now()
            
            # Mock weather data
            weather_conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear"]
            weather = {
                "condition": random.choice(weather_conditions),
                "temperature": random.randint(15, 30),
                "humidity": random.randint(30, 90)
            }
            
            response = {
                "time": current_time.strftime("%H:%M:%S"),
                "date": current_time.strftime("%Y-%m-%d"),
                "weather": f"{weather['condition']} {weather['temperature']}°C",
                "humidity": f"{weather['humidity']}%",
                "updated_at": current_time.isoformat()
            }
        else:
            response = {'status': 'ok', 'environment': 'vercel'}
            
        self.wfile.write(json.dumps(response).encode())
        return
        
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()
        
        # Get request body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        
        # Handle /ask endpoint
        if self.path == '/ask':
            if 'query' not in data:
                response = {'error': 'Query is required'}
                self.wfile.write(json.dumps(response).encode())
                return
            
            user_query = data['query']
            
            try:
                # Create a simplified prompt for the mirror
                simplified_prompt = (
                    "Imagine you are a magic mirror. You reflect the questions asked of you and offer answers in a clear, simple, and easy-to-understand way. "
                    "Avoid using complex words, bullet points, or special characters. Keep your responses short and sweet, so they are easy for anyone to understand. "
                    "You provide simple, natural answers as though you are a mirror reflecting the world around you. Don't make the answers too long. "
                    "Also, don't explicity say 'I am a mirror' or 'I reflect'. Just reflect the user's query in your response. "
                    "User's Question: " + user_query + "\nYour Response:"
                )
                
                # Use Gemini for response
                ai_response = model.generate_content(simplified_prompt)
                response_text = ai_response.text
            except Exception as e:
                response_text = f"I see you asked '{user_query}', but my reflection is cloudy at the moment. Try again later."
            
            response = {'response': response_text}
        else:
            response = {'error': 'Unknown endpoint'}
            
        self.wfile.write(json.dumps(response).encode())
        return
from http.server import BaseHTTPRequestHandler
import json
import datetime
import google.generativeai as genai
import os

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
            import random
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
            
            if API_KEY and 'gemini' in genai.__name__:
                try:
                    # Use Gemini for response
                    ai_response = model.generate_content(user_query)
                    response_text = ai_response.text
                except Exception as e:
                    response_text = f"AI service error: {str(e)}"
            else:
                # Fallback response if API key not configured
                response_text = f"I received your query: '{user_query}', but AI service is not configured."
            
            response = {'response': response_text}
        else:
            response = {'error': 'Unknown endpoint'}
            
        self.wfile.write(json.dumps(response).encode())
        return
from http.server import BaseHTTPRequestHandler
import json
import random

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()
        
        # Return mock data since this is running on Vercel, not Raspberry Pi
        # The real distance measurements will come from the hardware folder running on the Pi
        response = {
            'distance': round(random.uniform(10, 300), 2),
            'source': 'vercel_serverless'
        }
        
        self.wfile.write(json.dumps(response).encode())
        return
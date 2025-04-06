from flask import Flask, jsonify
import time
from flask_cors import CORS
import platform
import random

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Check if running on Windows or Raspberry Pi
is_raspberry_pi = platform.system() != "Windows"

# Only import GPIO libraries if on Raspberry Pi
if is_raspberry_pi:
    import RPi.GPIO as GPIO
    
    # Define GPIO pins
    TRIG = 23
    ECHO = 24
    
    # GPIO setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)

def measure_distance():
    if is_raspberry_pi:
        # Real implementation using GPIO
        GPIO.output(TRIG, False)
        time.sleep(0.5)
        
        # Send 10us pulse
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)
        
        # Wait for echo start
        while GPIO.input(ECHO) == 0:
            pulse_start = time.time()
        
        # Wait for echo end
        while GPIO.input(ECHO) == 1:
            pulse_end = time.time()
        
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # Speed of sound
        distance = round(distance, 2)
        return distance
    else:
        # Mock implementation for Windows development
        # Returns a random distance between 10 and 300 cm
        return round(random.uniform(10, 100), 2)
        # return 200.00  # Mock distance for testing

@app.route('/distance', methods=['GET'])
def get_distance():
    try:
        distance = measure_distance()
        print(distance)
        return jsonify({'distance': distance})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'platform': platform.system()})

if __name__ == '__main__':
    try:
        print(f"Starting server on platform: {platform.system()}")
        print(f"Using {'real' if is_raspberry_pi else 'mock'} distance sensor")
        app.run(host='0.0.0.0', port=5001)
    finally:
        if is_raspberry_pi:
            GPIO.cleanup()
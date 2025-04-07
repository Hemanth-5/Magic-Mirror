# hardware_server.py
from flask_cors import CORS  # Import CORS
from flask import Flask, jsonify, request
import platform
import os

try:
    import RPi.GPIO as GPIO
    import time
    IS_PI = True
except (ImportError, RuntimeError):
    IS_PI = False

app = Flask(__name__)
CORS(app, origin='*')  # Enable CORS for all routes

# GPIO Setup (only on Pi)
TRIG_PIN = 23
ECHO_PIN = 24

if IS_PI:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)

def get_distance():
    if not IS_PI:
        print("[MOCK] Returning fake distance: 100 cm")
        return 160.0

    # Ensure trigger is LOW
    GPIO.output(TRIG_PIN, False)
    time.sleep(0.1)

    # Send 10us pulse
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    # Measure echo time
    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return round(distance, 2)

def turn_off_screen():
    if IS_PI:
        os.system("vcgencmd display_power 0")
    print("🛌 Screen OFF command sent")

def turn_on_screen():
    if IS_PI:
        os.system("vcgencmd display_power 1")
    print("👀 Screen ON command sent")

@app.route('/distance', methods=['GET'])
def distance():
    try:
        dist = get_distance()
        return jsonify({'distance': dist})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/screen', methods=['POST'])
def control_screen():
    try:
        data = request.get_json()
        action = data.get("action")

        if action not in ["sleep", "wake"]:
            return jsonify({"error": "Invalid action"}), 400

        if action == "sleep":
            turn_off_screen()
        elif action == "wake":
            turn_on_screen()

        return jsonify({"status": "success", "action": action})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return "✅ Hardware server running on Raspberry Pi"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, ssl_context=('cert.pem', 'key.pem'))

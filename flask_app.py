from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import google.generativeai as genai
from collections import deque

API_KEY = "AIzaSyCyAUf1hgB3K6abvs5fuC2kQCk_NZToU8w"
genai.configure(api_key=API_KEY)

app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app)

# Initialize deque to store the last 10 messages (query, response pairs)
message_history = deque(maxlen=10)

def ask_google_assistant(prompt):
    """Send a text query to Google Bard API and get a simplified response."""
    
    # Combine the history messages into a single string
    history_text = "\n".join([f"User: {msg['query']}\nAssistant: {msg['response']}" for msg in message_history])
    
    simplified_prompt = (
        "Please provide a simple and easy-to-understand response to the following question. Also, avoid using markdowns such as bullet points, numbering, or special characters. "
        "Avoid complex terms, use everyday language, and provide clear and short sentences. "
        "Make it sound natural and easy for anyone to understand. Here is the conversation history:\n" + history_text + "\nQuestion: " + prompt
    )

    model = genai.GenerativeModel("gemini-1.5-flash")  # Corrected model name

    try:
        response = model.generate_content(simplified_prompt)
        return response.text if response else "Sorry, I didn't understand."
    except Exception as e:
        print(f"Error occurred: {e}")
        return "Sorry, I couldn't process your request."

@app.route('/ask', methods=['POST'])
def ask():
    """API endpoint to get AI response."""
    data = request.get_json()  # Get JSON data from the request
    if 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400

    user_query = data['query']
    print(f"Received query: {user_query}")

    # Get the response from the AI model
    response_text = ask_google_assistant(user_query)

    # Add the query and response to the message history
    message_history.append({'query': user_query, 'response': response_text})

    # Return the simplified response
    return jsonify({'response': response_text, 'history': list(message_history)})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

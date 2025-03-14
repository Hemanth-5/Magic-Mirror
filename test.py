import pyttsx3

# Initialize the pyttsx3 engine
engine = pyttsx3.init()

# Get the list of available voices
voices = engine.getProperty('voices')

# Loop through all available voices
for voice in voices:
    print(f"Voice: {voice.name}, ID: {voice.id}")  # Print voice details
    engine.setProperty('voice', voice.id)  # Set the voice

    # Create a passage, with high/low pitches to see how model reacts
    statement = "This is an important test, designed to push the limits of voice synthesis! I want you to listen carefully, and pay close attention to the words that I emphasize. How do you feel about artificial intelligence, and its growing impact on our daily lives? It’s fascinating, isn't it? But it’s also a bit unsettling... Don’t you agree?"
    for pitch in [50, 100, 150]:  # Different pitch levels
        engine.setProperty('pitch', pitch)  # Set the pitch
        engine.say(f"{statement} With pitch {pitch}")  # Say the statement with a specific pitch
        engine.runAndWait()  # Wait for speech to finish
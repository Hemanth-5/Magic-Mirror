import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import SpotifyPlayer from './SpotifyPlayer';
import MotionSensor from './MotionSensor';
import { handleSpotifyCallback } from './utils/SpotifyAuth';

const App = () => {
  const [time, setTime] = useState("--:--:--");
  const [date, setDate] = useState("--/--/----");
  const [sensorTemp, setSensorTemp] = useState("--°C");
  const [inputText, setInputText] = useState("");
  const [speechText, setSpeechText] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [isActivated, setIsActivated] = useState(false);
  const [hasActivated, setHasActivated] = useState(false);
  const [praise, setPraise] = useState("");
  const [spotifyPlayerState, setSpotifyPlayerState] = useState(null);
  const [showMusicPlayer, setShowMusicPlayer] = useState(false);
  const [isAwake, setIsAwake] = useState(true);
  const [data, setData] = useState(null);
  const [isVercel, setIsVercel] = useState(false);

  const canvasRef = useRef(null);
  const speechSynthesisRef = useRef({
    speaking: false,
    queue: [],
    processing: false
  });

  // Get environment variables with fallbacks
  const API_URL = process.env.REACT_APP_API_URL || window.location.origin;
  const HARDWARE_SERVER_URL = process.env.REACT_APP_HARDWARE_SERVER_URL || 'http://localhost:5001';
  
  // Detect if we're running on Vercel or locally
  useEffect(() => {
    // Check if the hostname contains vercel.app
    const isVercelEnv = window.location.hostname.includes('vercel.app');
    setIsVercel(isVercelEnv);
    console.log(`Running in ${isVercelEnv ? 'Vercel' : 'local'} environment`);
  }, []);

  const magicMirrorName = "magic";

  // Rest of your code remains the same...
  
  // Update time
  const updateTime = () => {
    const now = new Date();
    setTime(now.toLocaleTimeString());
    setDate(now.toLocaleDateString());
  };

  const getSensorTemp = async () => {
    try {
      const res = await fetch('http://<raspberry-pi-ip>:5001/dht');
      const data = await res.json();
      if (data?.temperature) {
        setSensorTemp(`${data.temperature}°C (${data.humidity}%)`);
      } else {
        setSensorTemp("N/A");
      }
    } catch (error) {
      console.error("Error fetching sensor temperature:", error);
      setSensorTemp("N/A");
    }
  };

  const speak = (text) => {
    if (!text || typeof text !== 'string' || text.trim() === '') {
      console.log("Empty text provided to speak function, ignoring.");
      return;
    }

    console.log("Trying to speak:", text);

    // Force cancel any existing speech to clear the queue
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    // Create utterance directly - simplifying the queue mechanism
    try {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      utterance.rate = 0.9;  // Slightly slower for better clarity
      utterance.pitch = 1;
      utterance.volume = 1.0; // Maximum volume
      
      // Log when speech starts
      utterance.onstart = () => {
        console.log("Speech started");
        speechSynthesisRef.current.speaking = true;
      };

      // Log when speech ends
      utterance.onend = () => {
        console.log("Speech ended");
        speechSynthesisRef.current.speaking = false;
      };

      // Log any errors
      utterance.onerror = (e) => {
        console.error("Speech error:", e);
        speechSynthesisRef.current.speaking = false;
      };

      // Check for voices and select a good one if available
      let voices = window.speechSynthesis.getVoices();
      if (voices.length === 0) {
        // Force voice loading if needed
        window.speechSynthesis.getVoices();
      }
      
      // Try to find a good voice - prefer Google voices
      voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(v =>
        v.name.toLowerCase().includes('google') &&
        v.lang.toLowerCase().includes('en') &&
        v.name.toLowerCase().includes('female')
      ) || voices.find(v =>
        v.name.toLowerCase().includes('google') &&
        v.lang.toLowerCase().includes('en')
      ) || voices.find(v =>
        v.lang.toLowerCase().includes('en') && v.name.toLowerCase().includes('female')
      ) || voices.find(v =>
        v.lang.toLowerCase().includes('en')
      );
      
      
      if (preferredVoice) {
        console.log("Using voice:", preferredVoice.name);
        utterance.voice = preferredVoice;
      }

      // Speak
      console.log("Calling speech synthesis speak()");
      window.speechSynthesis.speak(utterance);
      
      // Chrome bug workaround - if speech doesn't start after 1 second, try again
      setTimeout(() => {
        if (speechSynthesisRef.current.speaking === false) {
          console.log("Speech didn't start, trying again");
          window.speechSynthesis.cancel();
          window.speechSynthesis.speak(utterance);
        }
      }, 1000);
    } catch (error) {
      console.error("Error setting up speech synthesis:", error);
    }
  };

  // Remove the complex queue processing function since we're using a simpler approach
  const processSpeechQueue = () => {
    console.log("Speech queue processing is now handled directly in speak()");
  };

  const typeWriter = (text, setText) => {
    console.log("Typing:", text);
    let i = 0;
    let typedText = "";

    // Start speaking immediately
    speak(text);

    const interval = setInterval(() => {
      if (i < text.length) {
        typedText += text.charAt(i);
        setText(typedText);
        i++;
      } else {
        clearInterval(interval);
      }
    }, 50);
  };

  const sendToApi = async (query) => {
    try {
      // If in Vercel, use the deployed API, otherwise use localhost
      const apiUrl = isVercel ? `${API_URL}/ask` : "http://localhost:5000/ask";
      
      console.log(`Sending request to: ${apiUrl}`);
      
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();
      const aiMessage =
        data.response || data.message || "Sorry, no response received.";

      setAiResponse(aiMessage);

      // Only call typeWriter which will handle both typing and speaking
      typeWriter(aiMessage, setAiResponse);
      // Removing the duplicate speak call
      
      const musicRelatedTerms = [
        "playing", "music", "song", "track", "spotify", 
        "paused", "playlist", "artist", "album"
      ];

      const isMusicQuery = musicRelatedTerms.some(term => 
        aiMessage.toLowerCase().includes(term.toLowerCase())
      );

      if (isMusicQuery) {
        setShowMusicPlayer(true);
      }
    } catch (error) {
      console.error("API request error:", error);
      setAiResponse("Sorry, I couldn't process your request.");
      speak("Sorry, I couldn't process your request.");
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!isActivated && inputText.toLowerCase().includes(magicMirrorName)) {
      setIsActivated(true);
      setHasActivated(true);
      setAiResponse("Hello! I'm activated and ready for your questions.");
      speak("Hello! I'm activated and ready for your questions.");
      setInputText("");
    } else if (isActivated && inputText.trim() !== "") {
      setSpeechText(inputText);
      sendToApi(inputText);
      setInputText("");
    }
  };

  useEffect(() => {
    const timeInterval = setInterval(updateTime, 1000);
    const weatherInterval = setInterval(getWeather, 10000);
    const sensorInterval = setInterval(getSensorTemp, 10000);

    return () => {
      clearInterval(timeInterval);
      clearInterval(weatherInterval);
      clearInterval(sensorInterval);
    };
  }, []);

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setDate(now.toLocaleDateString());
      drawClock(now);
    };

    const drawClock = (now) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = 45;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
      ctx.fill();
      ctx.strokeStyle = "white";
      ctx.lineWidth = 2;
      ctx.stroke();

      const drawHand = (angle, length, width) => {
        ctx.beginPath();
        ctx.lineWidth = width;
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(
          centerX + length * Math.cos(angle),
          centerY + length * Math.sin(angle)
        );
        ctx.strokeStyle = "white";
        ctx.stroke();
      };

      const secondAngle = (now.getSeconds() / 60) * 2 * Math.PI - Math.PI / 2;
      const minuteAngle = (now.getMinutes() / 60) * 2 * Math.PI - Math.PI / 2;
      const hourAngle =
        ((now.getHours() % 12) / 12) * 2 * Math.PI - Math.PI / 2;

      drawHand(hourAngle, 25, 4);
      drawHand(minuteAngle, 35, 3);
      drawHand(secondAngle, 40, 1.5);
    };

    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Use the appropriate API URL based on environment
        const dataUrl = isVercel ? `${API_URL}/api/data` : `${API_URL}/api/data`;
        
        console.log(`Fetching data from: ${dataUrl}`);
        const response = await fetch(dataUrl);
        const result = await response.json();
        setData(result);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
    const intervalId = setInterval(fetchData, 300000);
    
    return () => clearInterval(intervalId);
  }, [API_URL, isVercel]);

  const handlePresenceChange = (isPresent) => {
    console.log('Presence changed:', isPresent);
    setIsAwake(isPresent);
  };

  const displayStyle = {
    transition: 'opacity 1s ease-in-out',
    opacity: isAwake ? 1 : 0,
    height: '100vh',
    width: '100vw',
    backgroundColor: '#000',
    color: '#fff',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '20px'
  };

  const praises = [
    "You're looking radiant today!",
    "That outfit looks fantastic on you!",
    "Your smile is absolutely glowing.",
    "Your confidence is shining through.",
    "You look stunning as always.",
    "Your eyes are sparkling today!",
    "That look is on point. You're rocking it!",
    "Your hair looks amazing—did you do something new?",
    "You've got that perfect glow today.",
    "You're looking sharp and stylish.",
    "You have a natural elegance about you.",
    "Your energy and style are so captivating.",
    "You've got that glow-up feeling today!",
    "Everything about your look is flawless.",
    "Your posture is perfect—own it!",
    "You look ready to take on the world!",
    "That color looks amazing on you.",
    "You make this look effortless—pure class.",
    "Your skin is glowing—looking healthy and refreshed.",
    "You're looking more confident with every day!",
  ];

  useEffect(() => {
    const randomPraise = praises[Math.floor(Math.random() * praises.length)];
    setPraise(". . .");
    setTimeout(() => {
      setPraise(randomPraise);
    }, 5000);
  }, []);

  // Clean up speech synthesis on component unmount
  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Add logic to handle Spotify login redirection
  const handleSpotifyLoginRedirect = () => {
    const API_URL = process.env.REACT_APP_API_URL || window.location.origin;
    window.location.href = `${API_URL}/login`; // Redirect to backend login endpoint
  };

  // Handle Spotify OAuth callback on app mount
  useEffect(() => {
    // Check if we're returning from Spotify OAuth
    handleSpotifyCallback((token) => {
      console.log('Spotify authentication successful');
      setShowMusicPlayer(true); // Show the music player when auth is successful
    });
  }, []);

  // Add this in the useEffect or componentDidMount of your main component
  useEffect(() => {
    const handleSpotifyAuthMessage = (event) => {
      if (event.data && event.data.type === 'SPOTIFY_AUTH_SUCCESS') {
        const { token } = event.data;
        localStorage.setItem('spotify_token', token);
        localStorage.setItem('spotify_token_timestamp', Date.now());
        console.log('Spotify token stored successfully:', token);
      }
    };

    // Add event listener for messages from the Spotify auth tab
    window.addEventListener('message', handleSpotifyAuthMessage);

    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener('message', handleSpotifyAuthMessage);
    };
  }, []);

  return (
    <div className="App">
      <div style={displayStyle}>
        {data && (
          <h1><div className="data-display">
            <div className="data-item weather">
              <strong> {data.weather}</strong>
            </div>
          </div></h1>
        )}
        <h1>
          <div className="praise">
            {isActivated ? praise : "Type 'magic' to activate."}
          </div>
        </h1>
        <div className="info-widget">
          <canvas ref={canvasRef} width="100" height="100"></canvas>
          <div className="date">{date}</div>
          <div className="weather-temp">
            <div>{sensorTemp}</div>
          </div>
          {/* {isVercel && (
            <div className="environment-badge">
              Running on Vercel
            </div>
          )} */}
        </div>

        <form onSubmit={handleSubmit} className="input-form">
          <input 
            type="text" 
            value={inputText} 
            onChange={(e) => setInputText(e.target.value)} 
            placeholder={isActivated ? "Ask me anything..." : "Type 'magic' to activate"}
            className="text-input"
          />
          <button type="submit" className="submit-btn">Send</button>
        </form>

        {showMusicPlayer && (
          <div className="spotify-container">
            <SpotifyPlayer onPlayerStateChange={setSpotifyPlayerState} onLoginRedirect={handleSpotifyLoginRedirect} />
          </div>
        )}

        {speechText && (
          <div className="speech-text show">
            <strong>You:</strong> {speechText}
          </div>
        )}

        {aiResponse && (
          <div className={`ai-response ${aiResponse ? "show" : ""}`}>
            <strong>Mirror:</strong> {aiResponse}
          </div>
        )}

      </div>
      
      {/* Only use MotionSensor when not in Vercel environment */}
      <MotionSensor onPresenceChange={handlePresenceChange}/>
    </div>
  );
};

export default App;

import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const recognition = new (window.SpeechRecognition ||
  window.webkitSpeechRecognition)();
recognition.continuous = true;
recognition.interimResults = true;

const App = () => {
  const [time, setTime] = useState("--:--:--");
  const [date, setDate] = useState("--/--/----");
  const [weatherTemp, setWeatherTemp] = useState("--°C");
  const [sensorTemp, setSensorTemp] = useState("--°C");
  const [isListening, setIsListening] = useState(false);
  const [speechText, setSpeechText] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [isActivated, setIsActivated] = useState(false); // Track activation status

  const canvasRef = useRef(null); // Ref for Analog Clock

  const magicMirrorName = "alexa"; // Set the name of the Magic Mirror

  const updateTime = () => {
    const now = new Date();
    setTime(now.toLocaleTimeString());
    setDate(now.toLocaleDateString());
  };

  const getWeather = () => {
    const temp = Math.floor(Math.random() * 10 + 20);
    setWeatherTemp(`${temp}°C`);
  };

  const getSensorTemp = () => {
    const sensorTemp = Math.floor(Math.random() * 5 + 25);
    setSensorTemp(`${sensorTemp}°C`);
  };

  const speak = (text) => {
    const synth = window.speechSynthesis;

    if (synth.speaking) {
      synth.cancel();
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = 1;
    utterance.pitch = 1;

    utterance.onend = () => {
      console.log("Speech finished completely");
    };

    utterance.onerror = (e) => {
      console.error("Speech error: ", e);
    };

    synth.speak(utterance);
  };

  const typeWriter = (text, setText) => {
    let i = 0;
    setText(text[i]);

    speak(text);

    const interval = setInterval(() => {
      if (i < text.length) {
        setText((prev) => prev + text[i]);
        i++;
      } else {
        clearInterval(interval);
      }
    }, 50);
  };

  const sendToApi = async (query) => {
    try {
      const response = await fetch("http://localhost:5000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();
      const aiMessage =
        data.response || data.message || "Sorry, no response received.";

      console.log(aiMessage);
      setAiResponse(aiMessage);

      typeWriter(aiMessage, setAiResponse);
    } catch (error) {
      setAiResponse("Sorry, I couldn't process your request.");
      speak("Sorry, I couldn't process your request.");
    }
  };

  const toggleMic = () => {
    const synth = window.speechSynthesis;

    if (synth.speaking) {
      synth.cancel();
    }

    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      recognition.start();
      setIsListening(true);
      setSpeechText("");
      setAiResponse("");
    }
  };

  const handleSpeechRecognition = (event) => {
    let finalTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      finalTranscript += result[0].transcript;
    }
    setSpeechText(finalTranscript);

    if (finalTranscript.toLowerCase().includes(magicMirrorName.toLowerCase())) {
      // Activate the magic mirror when the name is detected
      setIsActivated(true);
      speak("Hello! I'm activated and ready to listen.");
      setIsListening(true); // Continue listening after activation
    }

    if (isActivated && event.results[event.results.length - 1].isFinal) {
      sendToApi(finalTranscript);
    }
  };

  useEffect(() => {
    recognition.onresult = handleSpeechRecognition;

    const timeInterval = setInterval(updateTime, 1000);
    const weatherInterval = setInterval(getWeather, 10000);
    const sensorInterval = setInterval(getSensorTemp, 10000);

    return () => {
      clearInterval(timeInterval);
      clearInterval(weatherInterval);
      clearInterval(sensorInterval);
    };
  }, [isActivated]);

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

      // Draw clock face
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
      ctx.fill();
      ctx.strokeStyle = "white";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw clock hands
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

      // Get time angles
      const secondAngle = (now.getSeconds() / 60) * 2 * Math.PI - Math.PI / 2;
      const minuteAngle = (now.getMinutes() / 60) * 2 * Math.PI - Math.PI / 2;
      const hourAngle =
        ((now.getHours() % 12) / 12) * 2 * Math.PI - Math.PI / 2;

      // Draw hands
      drawHand(hourAngle, 25, 4); // Hour hand
      drawHand(minuteAngle, 35, 3); // Minute hand
      drawHand(secondAngle, 40, 1.5); // Second hand
    };

    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="App">
      <h1>
        <div className="praise">
          {isActivated ? "How can I assist you?" : "Say my name to activate."}
        </div>
      </h1>
      <div className="info-widget">
        <canvas ref={canvasRef} width="100" height="100"></canvas>
        <div className="date">{date}</div>
        <div className="weather-temp">
          <div>{weatherTemp}</div>
          <div>{sensorTemp}</div>
        </div>
      </div>

      <div
        className={`microphone-btn ${isListening ? "active" : ""}`}
        onClick={toggleMic}
      >
        <span className="pulse"></span>
        <div className="listening">
          {isListening ? "Listening..." : "Tap to Speak"}
        </div>
      </div>

      {speechText && (
        <div className="speech-text show">
          <strong></strong> {speechText}
        </div>
      )}

      {aiResponse && (
        <div className={`ai-response ${aiResponse ? "show" : ""}`}>
          <strong></strong> {aiResponse}
        </div>
      )}
    </div>
  );
};

export default App;

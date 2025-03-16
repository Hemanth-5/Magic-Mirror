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
  const [isActivated, setIsActivated] = useState(false); // Track activation
  const [hasActivated, setHasActivated] = useState(false); // Track first activation
  const [praise, setPraise] = useState(""); // Random praise message

  const canvasRef = useRef(null); // Ref for Analog Clock

  const magicMirrorName = "magic"; // Set the name of the Magic Mirror

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

    // Cancel any ongoing speech to allow interruption
    if (synth.speaking) {
      console.log("Interrupting ongoing speech...");
      synth.cancel();
    }

    // Ensure voices are ready
    if (synth.getVoices().length === 0) {
      console.error("Speech Synthesis voices are not ready yet.");
      setTimeout(() => speak(text), 1000);
      return;
    }

    // Split text into smaller sentences if needed
    const sentences = text.match(/[^.!?]+[.!?]/g) || [text];

    const speakSentence = (index = 0) => {
      if (index >= sentences.length) return; // Stop if done

      const utterance = new SpeechSynthesisUtterance(sentences[index].trim());
      utterance.lang = "en-US";
      utterance.rate = 1;
      utterance.pitch = 1;

      utterance.onend = () => {
        console.log("Speech finished:", sentences[index]);
        speakSentence(index + 1);
      };

      utterance.onerror = (e) => {
        console.error("Speech error: ", e);
      };

      synth.speak(utterance);
    };

    speakSentence(); // Start speaking
  };

  const typeWriter = (text, setText) => {
    console.log("Typing: ", text);
    let i = 0;
    let typedText = ""; // Accumulate the text

    const interval = setInterval(() => {
      if (i < text.length) {
        typedText += text.charAt(i); // Accumulate text
        setText(typedText); // Update state once with the accumulated text
        i++;
      } else {
        clearInterval(interval);
      }
    }, 50);

    speak(text); // Speak after starting the typewriter effect
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

      // console.log(aiMessage);
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
      setSpeechText(""); // Clear speech text when starting new listening session
      setAiResponse(""); // Clear AI response
    }
  };

  const handleSpeechRecognition = (event) => {
    let finalTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      finalTranscript += result[0].transcript;
    }
    setSpeechText(finalTranscript);

    // Check if the speech contains the activation phrase "magic"
    if (finalTranscript.toLowerCase().includes(magicMirrorName.toLowerCase())) {
      if (!isActivated) {
        // If it's the first time, activate and stop further processing
        setIsActivated(true);
        setHasActivated(true); // First activation
        speak("Hello! I'm activated and ready to listen.");
        return; // Prevent processing the query if it's just the activation phrase
      }
    }

    // Only process non-activation input after activation
    if (
      isActivated &&
      hasActivated &&
      event.results[event.results.length - 1].isFinal &&
      !finalTranscript.toLowerCase().includes(magicMirrorName.toLowerCase()) // Ensure it's not the activation phrase
    ) {
      sendToApi(finalTranscript); // Send the query to AI if it's not the activation phrase
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

  const praises = [
    "You’re looking radiant today!",
    "That outfit looks fantastic on you!",
    "Your smile is absolutely glowing.",
    "Your confidence is shining through.",
    "You look stunning as always.",
    "Your eyes are sparkling today!",
    "That look is on point. You’re rocking it!",
    "Your hair looks amazing—did you do something new?",
    "You’ve got that perfect glow today.",
    "You’re looking sharp and stylish.",
    "You have a natural elegance about you.",
    "Your energy and style are so captivating.",
    "You’ve got that glow-up feeling today!",
    "Everything about your look is flawless.",
    "Your posture is perfect—own it!",
    "You look ready to take on the world!",
    "That color looks amazing on you.",
    "You make this look effortless—pure class.",
    "Your skin is glowing—looking healthy and refreshed.",
    "You’re looking more confident with every day!",
  ];

  useEffect(() => {
    const randomPraise = praises[Math.floor(Math.random() * praises.length)];
    setPraise(". . .");
    setTimeout(() => {
      setPraise(randomPraise);
    }, 5000);
  }, []);

  return (
    <div className="App">
      <h1>
        <div className="praise">
          {isActivated ? praise : "Say my name to activate."}
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

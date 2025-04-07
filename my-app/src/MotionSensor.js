import React, { useEffect, useState, useRef } from 'react';

const MotionSensor = ({ onPresenceChange }) => {
  const [isPresent, setIsPresent] = useState(true);
  const [distance, setDistance] = useState(null);
  const [error, setError] = useState(null);
  const consistentAbsenceCountRef = useRef(0);
  
  // Get hardware URL from environment or use default
  const HARDWARE_SERVER_URL = process.env.REACT_APP_HARDWARE_SERVER_URL || 'http://localhost:5001';
  const PRESENCE_THRESHOLD = 150; // Distance in cm to determine presence
  const CHECK_INTERVAL = 5000; // Check every 5 seconds (5000ms)
  const REQUIRED_ABSENCE_COUNT = 2; // Need this many consecutive absence detections
  
  useEffect(() => {
    let intervalId = null;
    
    const checkDistance = async () => {
      try {
        // Fetch distance from the hardware API
        const response = await fetch(`${HARDWARE_SERVER_URL}/distance`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch distance: ${response.status}`);
        }
        
        const data = await response.json();
        const currentDistance = data.distance;
        
        setDistance(currentDistance);
        console.log(`Distance reading: ${currentDistance} cm (Absence count: ${consistentAbsenceCountRef.current}, Present: ${isPresent})`);
        
        // Determine if someone is present based on the distance
        const isSomeonePresent = currentDistance <= PRESENCE_THRESHOLD;
        
        if (isSomeonePresent) {
          // Reset absence counter
          consistentAbsenceCountRef.current = 0;
          
          // If we were away, now we're present
          if (!isPresent) {
            console.log('❗ Presence detected - waking up display');
            setIsPresent(true);
            onPresenceChange(true);
          }
        } else {
          // Increment absence counter
          consistentAbsenceCountRef.current++;
          console.log(`➕ No presence detected (${consistentAbsenceCountRef.current}/${REQUIRED_ABSENCE_COUNT})`);
          
          // If we've seen enough consecutive absence readings and we're still marked as present
          if (consistentAbsenceCountRef.current >= REQUIRED_ABSENCE_COUNT && isPresent) {
            console.log('💤 Absence confirmed - putting display to sleep');
            setIsPresent(false);
            onPresenceChange(false);
          }
        }
      } catch (err) {
        console.error('Error fetching distance:', err);
        setError(err.message);
        // Don't change presence state on error
      }
    };

    // Initial check
    consistentAbsenceCountRef.current = 0;
    checkDistance();
    
    // Set up periodic checking with the specified interval
    console.log(`Setting up distance check interval: ${CHECK_INTERVAL}ms`);
    intervalId = setInterval(checkDistance, CHECK_INTERVAL);
    
    // Clean up function
    return () => {
      console.log('Cleaning up motion sensor interval');
      clearInterval(intervalId);
    };
  // Remove isPresent from dependency array to prevent re-creating interval
  }, [onPresenceChange, HARDWARE_SERVER_URL]);

  // Optional debugging display (only in development mode)
  const debugStyle = {
    position: 'absolute',
    bottom: 10,
    left: 10,
    backgroundColor: 'rgba(0,0,0,0.7)',
    color: 'white',
    padding: '5px',
    borderRadius: '5px',
    fontSize: '12px',
    display: process.env.NODE_ENV === 'development' ? 'block' : 'none'
  };

  return (
    <>
      {/* Hidden component - only used for logic */}
      {process.env.NODE_ENV === 'development' && (
        <div style={debugStyle}>
          <div>Current: {distance !== null ? `${distance} cm` : 'Loading...'}</div>
          <div>Absence Count: {consistentAbsenceCountRef.current}/{REQUIRED_ABSENCE_COUNT}</div>
          {error && <div style={{ color: 'red' }}>Error: {error}</div>}
          <div>Status: {isPresent ? 'Present ✓' : 'Away ✗'}</div>
        </div>
      )}
    </>
  );
};

export default MotionSensor;
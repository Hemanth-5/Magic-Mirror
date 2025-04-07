import React, { useEffect, useState, useRef } from 'react';

const MotionSensor = ({ onPresenceChange }) => {
  const [isPresent, setIsPresent] = useState(true);
  const [distance, setDistance] = useState(null);
  const [error, setError] = useState(null);
  const consistentAbsenceCountRef = useRef(0);

  const HARDWARE_SERVER_URL = process.env.REACT_APP_HARDWARE_SERVER_URL || 'http://localhost:5001';
  const PRESENCE_THRESHOLD = 150;
  const CHECK_INTERVAL = 5000;
  const REQUIRED_ABSENCE_COUNT = 2;

  const handlePresenceChange = async (present) => {
    const action = present ? 'wake' : 'sleep';

    try {
      await fetch(`${HARDWARE_SERVER_URL}/screen`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      console.log(`✅ Screen ${action.toUpperCase()} command sent`);
    } catch (err) {
      console.error(`❌ Failed to send screen ${action} request`, err);
    }

    onPresenceChange(present); // still notify parent
  };

  useEffect(() => {
    let intervalId = null;

    const checkDistance = async () => {
      try {
        const response = await fetch(`${HARDWARE_SERVER_URL}/distance`);
        if (!response.ok) throw new Error(`Distance fetch failed: ${response.status}`);
        const data = await response.json();
        const currentDistance = data.distance;

        setDistance(currentDistance);
        const isSomeonePresent = currentDistance <= PRESENCE_THRESHOLD;

        if (isSomeonePresent) {
          consistentAbsenceCountRef.current = 0;

          if (!isPresent) {
            console.log('🙋 Presence detected');
            setIsPresent(true);
            handlePresenceChange(true);
          }
        } else {
          consistentAbsenceCountRef.current++;
          console.log(`🤷 No presence (${consistentAbsenceCountRef.current}/${REQUIRED_ABSENCE_COUNT})`);

          if (consistentAbsenceCountRef.current >= REQUIRED_ABSENCE_COUNT && isPresent) {
            console.log('😴 Absence confirmed');
            setIsPresent(false);
            handlePresenceChange(false);
          }
        }
      } catch (err) {
        console.error('Error in distance check:', err);
        setError(err.message);
      }
    };

    consistentAbsenceCountRef.current = 0;
    checkDistance();
    intervalId = setInterval(checkDistance, CHECK_INTERVAL);

    return () => {
      clearInterval(intervalId);
      console.log('🔁 Cleared interval');
    };
  }, [onPresenceChange, HARDWARE_SERVER_URL]);

  const debugStyle = {
    position: 'absolute',
    bottom: 10,
    left: 10,
    backgroundColor: 'rgba(0,0,0,0.7)',
    color: 'white',
    padding: '5px',
    borderRadius: '5px',
    fontSize: '12px',
    display: process.env.NODE_ENV === 'development' ? 'block' : 'none',
  };

  return (
    <>
      {(
        <div style={debugStyle}>
          <div>Distance: {distance !== null ? `${distance} cm` : 'Loading...'}</div>
          <div>Absence Count: {consistentAbsenceCountRef.current}/{REQUIRED_ABSENCE_COUNT}</div>
          <div>Status: {isPresent ? 'Present ✓' : 'Away ✗'}</div>
          {error && <div style={{ color: 'red' }}>Error: {error}</div>}
        </div>
      )}
    </>
  );
};

export default MotionSensor;

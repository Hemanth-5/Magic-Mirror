import React, { useState, useEffect } from 'react';
import './SpotifyPlayer.css';

const SpotifyPlayer = ({ onPlayerStateChange }) => {
  const [player, setPlayer] = useState(null);
  const [deviceId, setDeviceId] = useState('');
  const [isActive, setIsActive] = useState(false);
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPaused, setIsPaused] = useState(true);
  const [error, setError] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [progressTimer, setProgressTimer] = useState(null);
  const [isVercelEnv, setIsVercelEnv] = useState(false);

  useEffect(() => {
    // Detect if running on Vercel or locally
    const isVercelEnvironment = window.location.hostname.includes('vercel.app');
    setIsVercelEnv(isVercelEnvironment);
    
    if (isVercelEnvironment) {
      console.log('Running on Vercel - Spotify integration will use mock data');
      // Set up mock data for Vercel environment
      setCurrentTrack({
        name: 'Demo Track (Vercel Mode)',
        artist: 'Example Artist',
        image: 'https://via.placeholder.com/300'
      });
      setIsActive(true);
      setIsPaused(false);
      setDuration(180); // 3 minutes mock song
      
      // Start mock progress timer
      const timer = setInterval(() => {
        setProgress(prev => {
          if (prev >= 180) return 0; // Loop at 3 minutes
          return prev + 0.1;
        });
      }, 100);
      
      return () => clearInterval(timer);
    }
    
    // Function to initialize the Spotify Web Playback SDK (only for non-Vercel environments)
    const initializePlayer = async () => {
      // Don't re-initialize if already done
      if (isInitialized) return;
      setIsInitialized(true);
      
      try {
        // Get token from backend
        const API_URL = process.env.REACT_APP_API_URL || window.location.origin;
        const response = await fetch(`${API_URL}/get-spotify-token`);
        const data = await response.json();
        
        if (response.status !== 200) {
          throw new Error(data.error || 'Failed to retrieve Spotify token');
        }
        
        const token = data.token;
        if (!token) {
          throw new Error('No Spotify token available');
        }

        console.log('Retrieved Spotify token successfully');

        // Create the player
        const spotifyPlayer = new window.Spotify.Player({
          name: 'Magic Mirror Spotify Player',
          getOAuthToken: cb => { cb(token); },
          volume: 0.5
        });

        // Error handling
        spotifyPlayer.addListener('initialization_error', ({ message }) => {
          console.error('Initialization error:', message);
          setError(`Initialization error: ${message}`);
        });
        
        spotifyPlayer.addListener('authentication_error', ({ message }) => {
          console.error('Authentication error:', message);
          setError(`Authentication error: ${message}`);
        });
        
        spotifyPlayer.addListener('account_error', ({ message }) => {
          console.error('Account error:', message);
          setError(`Account error: ${message}`);
        });
        
        spotifyPlayer.addListener('playback_error', ({ message }) => {
          console.error('Playback error:', message);
          setError(`Playback error: ${message}`);
        });

        // Ready
        spotifyPlayer.addListener('ready', ({ device_id }) => {
          console.log('Spotify Player Ready with Device ID:', device_id);
          setDeviceId(device_id);
          setPlayer(spotifyPlayer);
          setIsActive(true); // Mark as active when ready
          setError(null);
          
          // Tell the backend about this player
          fetch(`${API_URL}/set-active-device`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_id })
          }).then(response => {
            if (!response.ok) {
              console.error('Failed to set active device');
            }
          });
          
          // Force a transfer to this device to make it active
          fetch('https://api.spotify.com/v1/me/player', {
            method: 'PUT',
            headers: { 
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              device_ids: [device_id],
              play: false
            })
          });
        });

        // Not Ready
        spotifyPlayer.addListener('not_ready', ({ device_id }) => {
          console.log('Spotify Player has gone offline:', device_id);
          setIsActive(false);
        });

        // Player State Changed
        spotifyPlayer.addListener('player_state_changed', (state) => {
          if (!state) {
            setIsActive(false);
            return;
          }
          
          const trackInfo = state.track_window?.current_track;
          
          if (trackInfo) {
            setCurrentTrack({
              name: trackInfo.name || 'Unknown Track',
              artist: trackInfo.artists ? trackInfo.artists[0]?.name || 'Unknown Artist' : 'Unknown Artist',
              image: trackInfo.album?.images?.[0]?.url || ''
            });
          } else {
            setCurrentTrack(null);
          }
          
          setIsPaused(state.paused);
          setIsActive(true);
          setProgress(state.position / 1000);
          setDuration(state.duration / 1000);
          
          if (onPlayerStateChange) {
            onPlayerStateChange(state);
          }
        });

        // Connect to Spotify
        console.log('Connecting to Spotify...');
        const connected = await spotifyPlayer.connect();
        
        if (connected) {
          console.log('Connected to Spotify!');
        } else {
          console.error('Failed to connect to Spotify');
          setError('Failed to connect to Spotify');
        }
        
      } catch (error) {
        console.error('Spotify Player Error:', error);
        setError(`Error: ${error.message}`);
      }
    };

    // Only initialize when component is mounted and not in Vercel env
    if (window.Spotify && !isVercelEnvironment) {
      initializePlayer();
    } else if (!isVercelEnvironment) {
      // If the SDK isn't loaded yet, wait for it
      window.onSpotifyWebPlaybackSDKReady = () => {
        initializePlayer();
      };
    }

    return () => {
      if (player) {
        player.disconnect();
      }
      if (progressTimer) {
        clearInterval(progressTimer);
      }
    };
  }, [onPlayerStateChange, isInitialized, progressTimer]);

  // Update progress bar in real time when playing
  useEffect(() => {
    if (progressTimer) {
      clearInterval(progressTimer);
    }
    
    if (!isPaused && isActive) {
      const timer = setInterval(() => {
        setProgress(prev => {
          if (prev >= duration) {
            clearInterval(timer);
            return duration;
          }
          return prev + 0.1;
        });
      }, 100);
      
      setProgressTimer(timer);
      
      return () => clearInterval(timer);
    }
  }, [isPaused, isActive, duration]);

  const handlePlayPause = () => {
    if (isVercelEnv) {
      // Mock behavior for Vercel
      setIsPaused(!isPaused);
      return;
    }
    
    if (player) {
      player.togglePlay();
    }
  };

  const handlePrevious = () => {
    if (isVercelEnv) {
      // Mock behavior for Vercel
      setProgress(0);
      return;
    }
    
    if (player) {
      player.previousTrack();
    }
  };

  const handleNext = () => {
    if (isVercelEnv) {
      // Mock behavior for Vercel
      // Simulate going to next track by resetting progress
      setProgress(0);
      return;
    }
    
    if (player) {
      player.nextTrack();
    }
  };

  const handleProgressClick = (e) => {
    if ((!player && !isVercelEnv) || !duration) return;
    
    const progressBar = e.currentTarget;
    const clickPosition = e.nativeEvent.offsetX / progressBar.offsetWidth;
    const newPosition = clickPosition * duration;
    
    setProgress(newPosition);
    
    if (!isVercelEnv && player) {
      player.seek(newPosition * 1000);
    }
  };
  
  if (error && !isVercelEnv) {
    return (
      <div className="spotify-player error">
        <div className="player-status">
          <p>Spotify player error:</p>
          <p>{error}</p>
          <p>Make sure you're logged into Spotify and have an active Premium account.</p>
        </div>
      </div>
    );
  }

  if (!isActive && !isVercelEnv) {
    return (
      <div className="spotify-player inactive">
        <div className="player-status">
          <p>Spotify player is initializing...</p>
          <p className="small">Please open the Spotify app on your device to help with connection.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`spotify-player ${!isActive ? 'inactive' : ''}`}>
      {currentTrack ? (
        <>
          <div className="now-playing">
            <img 
              src={currentTrack.image} 
              alt={`${currentTrack.name} by ${currentTrack.artist}`}
              className="album-art"
            />
            <div className="track-info">
              <div className="track-name">{currentTrack.name}</div>
              <div className="artist-name">{currentTrack.artist}</div>
              <div className="progress-bar" onClick={handleProgressClick}>
                <div 
                  className="progress-bar-filled" 
                  style={{ width: `${(progress / duration) * 100}%` }}
                ></div>
              </div>
              <div className="time-stamps">
                <span>{formatTime(progress)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>
          </div>
  
          <div className="player-controls">
            <button onClick={handlePrevious} className="control-button" title="Previous">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M13 2.5L5 7.5v-5H3v11h2v-5l8 5V2.5z"></path>
              </svg>
            </button>
            <button onClick={handlePlayPause} className="control-button play-pause" title="Play/Pause">
              {isPaused ? (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M4.018 14L14.41 8 4.018 2z"></path>
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path fill="none" d="M0 0h16v16H0z"></path>
                  <path d="M3 2h3v12H3zm7 0h3v12h-3z"></path>
                </svg>
              )}
            </button>
            <button onClick={handleNext} className="control-button" title="Next">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M11 3v5l-8-5v11l8-5v5h2V3z"></path>
              </svg>
            </button>
          </div>
          
          {isVercelEnv && (
            <div className="vercel-notice">
              <p className="small">Demo mode (Vercel deployment)</p>
            </div>
          )}
        </>
      ) : (
        <div className="no-track">
          <p>Ready to play music</p>
          <p className="small">Try saying "Play some jazz" or "Play Taylor Swift"</p>
          {isVercelEnv && <p className="small">(Demo mode on Vercel)</p>}
        </div>
      )}
    </div>
  );
  
};

const formatTime = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs < 10 ? '0' : ''}${secs}`;
};

export default SpotifyPlayer;
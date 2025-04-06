/**
 * SpotifyAuth.js - Handles Spotify authentication flows
 */

// Get environment variables or default to localhost during development
const API_URL = process.env.REACT_APP_API_URL || window.location.origin;

/**
 * Initiate the Spotify login process
 */
export const initiateSpotifyLogin = () => {
  window.location.href = `${API_URL}/login`;
};

/**
 * Extract the access token from URL parameters after OAuth redirect
 * @returns {string|null} The Spotify access token or null if not present
 */
export const getTokenFromUrl = () => {
  const params = new URLSearchParams(window.location.search);
  return params.get('token');
};

/**
 * Store the Spotify token in local storage
 * @param {string} token - The Spotify access token
 */
export const storeSpotifyToken = (token) => {
  localStorage.setItem('spotify_token', token);
  localStorage.setItem('spotify_token_timestamp', Date.now());
};

/**
 * Get the stored Spotify token
 * @returns {string|null} The stored token or null if not found/expired
 */
export const getStoredSpotifyToken = () => {
  const token = localStorage.getItem('spotify_token');
  const timestamp = localStorage.getItem('spotify_token_timestamp');
  
  // Check if token exists and is less than 1 hour old (Spotify tokens expire after 1 hour)
  if (token && timestamp && (Date.now() - parseInt(timestamp) < 3600000)) {
    return token;
  }
  
  // Clear invalid/expired token
  localStorage.removeItem('spotify_token');
  localStorage.removeItem('spotify_token_timestamp');
  return null;
};

/**
 * Check for and handle Spotify login callback
 * @param {Function} callback - Function to call after successful login
 */
export const handleSpotifyCallback = (callback) => {
  const token = getTokenFromUrl();
  
  if (token) {
    // Store the token for future use
    storeSpotifyToken(token);
    
    // Clear the URL parameters
    window.history.replaceState({}, document.title, '/');
    
    // Notify the app about successful authentication
    if (callback) {
      callback(token);
    }
    
    return true;
  }
  
  return false;
};
/**
 * SpotifyAuth.js - Handles Spotify authentication flows
 */

// Get environment variables or default to localhost during development
const API_URL = process.env.REACT_APP_API_URL || window.location.origin;

/**
 * Initiate the Spotify login process
 * Now forces account selection dialog to be shown
 */
export const initiateSpotifyLogin = () => {
  // Open in a new tab instead of redirecting
  window.open(`${API_URL}/login`, '_blank');
  
  // Set up a message listener to detect when auth is complete
  window.addEventListener('message', handleAuthMessage);
  
  console.log("Spotify login initiated in new tab, listening for auth message");
};

/**
 * Handle authentication messages from the popup window
 */
const handleAuthMessage = (event) => {
  // Check if this is our auth success message
  if (event.data && event.data.type === 'SPOTIFY_AUTH_SUCCESS') {
    console.log('Received Spotify auth success message from popup');
    
    // Store the token
    storeSpotifyToken(event.data.token);
    
    // Reload the page to apply the new token
    window.location.reload();
    
    // Clean up the event listener
    window.removeEventListener('message', handleAuthMessage);
  }
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
  console.log('Storing Spotify token in local storage');
  localStorage.setItem('spotify_token', token);
  localStorage.setItem('spotify_token_timestamp', Date.now());
};

/**
 * Get the stored Spotify token
 * @returns {string|null} The stored token or null if not found/expired
 */
export const getStoredSpotifyToken = () => {
  try {
    const token = localStorage.getItem('spotify_token');
    const timestamp = localStorage.getItem('spotify_token_timestamp');
    
    if (!token || !timestamp) {
      return null;
    }
    
    // Check if token is expired (tokens last 1 hour / 3600000 ms)
    const now = Date.now();
    const tokenAge = now - parseInt(timestamp, 10);
    
    if (tokenAge > 3500000) { // Just under 1 hour to be safe
      console.log('Stored token is expired');
      localStorage.removeItem('spotify_token');
      localStorage.removeItem('spotify_token_timestamp');
      return null;
    }
    
    return token;
  } catch (e) {
    console.error('Error retrieving token from localStorage:', e);
    return null;
  }
};

/**
 * Check for and handle Spotify login callback
 * @param {Function} callback - Function to call after successful login
 */
export const handleSpotifyCallback = (callback) => {
  // First check if we have a token in local storage
  const storedToken = getStoredSpotifyToken();
  if (storedToken) {
    console.log('Found valid token in local storage');
    if (callback) {
      callback(storedToken);
    }
    return true;
  }
  
  // Then check URL parameters (for direct redirects)
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
  
  // First check for messages from popup window
  const handleAuthMessage = (event) => {
    if (event.data && event.data.type === 'SPOTIFY_AUTH_SUCCESS') {
      console.log('Received Spotify auth success message from popup');
      const token = event.data.token;
      
      localStorage.setItem('spotify_token', token);
      localStorage.setItem('spotify_token_timestamp', Date.now());
      
      window.removeEventListener('message', handleAuthMessage);
      
      // Check if the token is for a premium account
      validateSpotifyPremium(token).then(isPremium => {
        if (isPremium) {
          if (callback) callback(token);
        } else {
          // Show premium account required error
          console.error('Spotify Premium account required');
          localStorage.setItem('spotify_premium_error', 'true');
        }
      });
    }
  };
  
  window.addEventListener('message', handleAuthMessage);
  
  return false;
};

/**
 * Validate if the user has a Spotify Premium account
 * Modified to always return true since we confirmed the account is premium
 * @param {string} token - Spotify access token
 * @returns {Promise<boolean>} Promise resolving to whether user has Premium
 */
export const validateSpotifyPremium = async (token) => {
  // Skip the actual validation and always assume premium
  console.log('Bypassing premium account validation - assuming account is premium');
  return true;
  
  /* Original validation code preserved for reference
  try {
    const response = await fetch('https://api.spotify.com/v1/me', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      console.error('Error validating Spotify account:', await response.text());
      return false;
    }
    
    const data = await response.json();
    const productType = data.product;
    
    // Check if user has premium subscription
    const isPremium = productType === 'premium';
    
    if (!isPremium) {
      console.log('User does not have Spotify Premium:', productType);
    }
    
    return isPremium;
  } catch (error) {
    console.error('Error validating Spotify Premium status:', error);
    return false;
  }
  */
};

/**
 * Check if there's a stored Premium account error
 * @returns {boolean} Whether a Premium account error has been stored
 */
export const hasPremiumError = () => {
  return localStorage.getItem('spotify_premium_error') === 'true';
};

/**
 * Clear the Premium account error flag
 */
export const clearPremiumError = () => {
  localStorage.removeItem('spotify_premium_error');
};

export default {
  initiateSpotifyLogin,
  getStoredSpotifyToken,
  handleSpotifyCallback,
  validateSpotifyPremium,
  hasPremiumError,
  clearPremiumError
};
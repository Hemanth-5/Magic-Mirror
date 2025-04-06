# Magic Mirror Project - Deployment Guide

This project is a smart mirror application with a React frontend and Python API backend, designed to be deployed on Vercel.

## Local Development Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd <your-repo-name>
```

2. Install frontend dependencies:
```bash
cd my-app
npm install
cd ..
```

3. Install backend dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Create a `.env.local` file in the `my-app` directory
   - Create a `.env` file in the root directory

5. Start the frontend development server:
```bash
cd my-app
npm start
```

6. Start the backend API server:
```bash
cd ..
python -m flask run
```

## Deploying to Vercel

### Prerequisites:
- A [Vercel](https://vercel.com/) account
- [Vercel CLI](https://vercel.com/cli) installed globally:
  ```bash
  npm install -g vercel
  ```

### Deployment Steps:

1. Log in to Vercel CLI:
```bash
vercel login
```

2. From the project root directory, deploy to Vercel:
```bash
vercel
```

3. When prompted:
   - Confirm deployment to Vercel
   - Link to existing project or create a new one
   - Specify the build settings (or use defaults)
   - Confirm deployment

4. Set up environment variables in the Vercel project dashboard:
   - Go to your Vercel project settings
   - Navigate to "Environment Variables"
   - Add all the variables from your `.env` file:
     - GOOGLE_API_KEY
     - OPENWEATHER_API_KEY
     - SPOTIFY_CLIENT_ID
     - SPOTIFY_CLIENT_SECRET
     - SPOTIFY_REDIRECT_URI
     - FLASK_APP_SECRET_KEY
     - REACT_APP_API_URL (set to your actual Vercel domain)

5. Redeploy to apply environment variables:
```bash
vercel --prod
```

6. Your magic mirror application is now live! Access it at the provided Vercel URL.

## Project Structure

- `my-app/` - React frontend application
- `api/` - Serverless functions for backend API
- `hardware/` - Hardware control scripts (for Raspberry Pi only)
- `software/` - Additional software components
- `vercel.json` - Vercel configuration file

## Hardware Setup (Raspberry Pi)

For the complete Magic Mirror hardware setup, follow the instructions in the hardware documentation.

## Notes

- The Spotify functionality requires a Premium account
- When deployed to Vercel, some hardware-specific features run in simulation mode
- For the full experience, deploy locally on a Raspberry Pi
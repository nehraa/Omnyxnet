# Pangea Net Website - Quick Start Guide

This guide will help you get the enhanced website running with all its new features.

## What's New

1. **Cloud Outages Evidence Board** - A detective-themed page showing real cloud service failures
2. **Backend API Server** - Store survey responses and fetch real-time outage data
3. **Enhanced Visuals** - Beautiful background patterns and animations throughout

## Quick Start (2 minutes)

### Option 1: With Backend API (Recommended)

**Step 1: Install Dependencies**
```bash
cd website/server
pip install -r requirements.txt
```

**Step 2: Set API Key (Optional)**
```bash
# Copy the environment template
cp .env.example .env

# Edit .env and add your Perplexity API key (optional - has fallback data)
# PERPLEXITY_API_KEY=your-key-here
```

**Step 3: Start Backend Server**
```bash
python app.py
```

The server will start on http://localhost:5000

**Step 4: Start Web Server**

In a new terminal:
```bash
cd website
python3 -m http.server 8080
```

**Step 5: Open Browser**

Visit: http://localhost:8080/index.html

### Option 2: Frontend Only (No Backend)

If you just want to view the website without the backend:

```bash
cd website
python3 -m http.server 8080
```

Visit: http://localhost:8080/index.html

**Note:** Survey submissions and outages data won't work without the backend, but you can still see the design.

## Key Pages

- **Homepage**: `http://localhost:8080/index.html`
- **Cloud Outages Board**: `http://localhost:8080/pages/outages.html`
- **Survey**: `http://localhost:8080/pages/survey.html`
- **About**: `http://localhost:8080/pages/about.html`
- **Technical**: `http://localhost:8080/pages/technical.html`

## Features to Try

### 1. Cloud Outages Evidence Board
- Visit `/pages/outages.html`
- See the detective board aesthetic with cork background
- Notice the polaroid-style incident cards
- Hover over cards to see them straighten and enlarge
- Look for red yarn connections between incidents
- Check the statistics at the top showing total impact
- Click "Refresh Data" to fetch latest information

### 2. Survey Form
- Visit `/pages/survey.html`
- Fill out the 7-question survey
- Your responses are saved to the backend (if running)
- Check `website/server/data/survey_responses.json` to see stored data

### 3. API Endpoints
Test the backend API:

```bash
# Health check
curl http://localhost:5000/api/health

# Get outages data
curl http://localhost:5000/api/outages | python3 -m json.tool

# Get survey statistics
curl http://localhost:5000/api/survey/stats | python3 -m json.tool

# Submit a test survey response
curl -X POST http://localhost:5000/api/survey \
  -H "Content-Type: application/json" \
  -d '{"q1": 5, "q2": "yes", "q3": "speed", "q4": "definitely", "q5": "storage", "q6": "immediately", "email": "test@example.com"}'
```

## Perplexity API Integration

The outages board can fetch real-time cloud outage data using Perplexity AI:

1. **Get API Key**: Sign up at https://www.perplexity.ai/
2. **Set Environment Variable**:
   ```bash
   export PERPLEXITY_API_KEY="pplx-..."
   ```
   Or add it to `website/server/.env`

3. **Data Updates**: 
   - Data is cached for 1 hour
   - Click "Refresh Data" button to force update
   - Fallback data is used if API is unavailable

## Troubleshooting

### Backend won't start
```bash
# Make sure you're in the right directory
cd website/server

# Install dependencies
pip install -r requirements.txt

# Check Python version (needs 3.8+)
python --version
```

### Survey submissions not saving
- Make sure backend is running on port 5000
- Check browser console for errors (F12)
- Verify `website/server/data/` directory exists

### Outages board shows "Error loading data"
- Backend server must be running
- Check that port 5000 is accessible
- Look at backend logs for error messages

### Fonts not loading
- This is normal for local development
- The website still works, just uses fallback fonts
- In production, Google Fonts will load properly

## File Structure

```
website/
├── index.html              # Main homepage
├── pages/
│   ├── outages.html       # NEW: Cloud outages evidence board
│   ├── survey.html        # Survey form (now connected to backend)
│   ├── about.html         # About page
│   ├── technical.html     # Technical details
│   └── demo.html          # CLI demo
├── css/
│   └── styles.css         # Enhanced with new patterns
├── js/
│   └── main.js            # Interactive features
└── server/                # NEW: Backend API
    ├── app.py             # Flask server
    ├── requirements.txt   # Dependencies
    ├── README.md          # API documentation
    ├── .env.example       # Configuration template
    └── data/              # Data storage (gitignored)
        ├── survey_responses.json
        └── outages_cache.json
```

## Design Elements

### Evidence Board Theme
- **Background**: Cork board texture with brown gradient
- **Cards**: Polaroid-style with subtle rotation
- **Connections**: Red yarn (SVG paths) between incidents
- **Pins**: 📌 emoji decorations
- **Font**: Special Elite for typewriter/detective feel
- **Stats**: Dashed red border boxes with pin decorations
- **Badges**: Red badges for security breaches and data loss

### Homepage Enhancements
- **Particle backgrounds**: Subtle dot patterns
- **Gradient overlays**: Depth and visual interest
- **Network patterns**: Connected nodes in tech section
- **Floating elements**: Animated decorative orbs

## Production Deployment

For production deployment:

1. **Backend**: Use Gunicorn instead of Flask dev server
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Frontend**: Use proper web server (nginx, Apache, etc.)

3. **Environment Variables**: Set via your hosting platform
   - `PERPLEXITY_API_KEY`
   - `PORT` (if needed)

4. **CORS**: Update CORS settings in `app.py` to restrict to your domain

5. **HTTPS**: Use SSL certificates for production

## Support

For issues or questions:
- Check the `website/server/README.md` for API documentation
- Review browser console for frontend errors
- Check backend logs for server errors
- Open an issue on GitHub

## Credits

- **Design**: Inspired by detective conspiracy boards
- **Data**: Perplexity AI for real-time cloud outage information
- **Icons**: Emoji for visual elements
- **Fonts**: Special Elite (Google Fonts) for detective theme

---

**Enjoy exploring the enhanced Pangea Net website! 🚀**

# Pangea Net Website Backend

Simple Flask API server for the Pangea Net website, providing survey form storage and cloud outage news data.

## Features

- **Survey Form Storage**: Stores survey responses in JSON format
- **Cloud Outages API**: Fetches real-time cloud service outage data using Perplexity AI
- **CORS Support**: Allows frontend requests from any origin
- **Caching**: Caches outage data for 1 hour to reduce API calls

## Setup

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
cd website/server
pip install -r requirements.txt
```

### Running the Server

```bash
python app.py
```

The server will start on `http://localhost:5000` by default.

### Environment Variables

- `PORT`: Server port (default: 5000)
- `FLASK_DEBUG`: Enable debug mode for development (default: false, **NEVER enable in production**)
- `PERPLEXITY_API_KEY`: API key for Perplexity AI (optional, has fallback data)

## API Endpoints

### POST /api/survey

Submit a survey response.

**Request Body:**
```json
{
  "q1": 5,
  "q2": "yes",
  "q3": "speed",
  "q4": "definitely",
  "q5": "storage",
  "q6": "immediately",
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Survey response saved successfully",
  "id": "20250101120000000000"
}
```

### GET /api/survey/stats

Get aggregated survey statistics.

**Response:**
```json
{
  "total_responses": 42,
  "q1_stats": {
    "5": 28,
    "4": 10,
    "3": 4
  },
  ...
}
```

### GET /api/outages

Fetch cloud service outages data (cached for 1 hour).

**Response:**
```json
{
  "outages": [
    {
      "company": "AWS",
      "date": "2024-06-13",
      "duration_hours": 4.5,
      "financial_loss_millions": 250,
      "affected_users": 15000000,
      "description": "...",
      "security_incident": false,
      "data_loss": false
    }
  ],
  "totals": {
    "total_incidents": 10,
    "total_duration_hours": 67.8,
    "total_financial_loss_millions": 3130,
    "total_affected_users": 124500000,
    "security_incidents": 2,
    "data_loss_incidents": 3
  },
  "last_updated": "2025-01-01T12:00:00"
}
```

### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-01T12:00:00"
}
```

## Data Storage

All data is stored in the `data/` directory:

- `survey_responses.json`: Survey form submissions
- `outages_cache.json`: Cached outage data from Perplexity API

## Perplexity API Integration

The server uses the Perplexity AI API to fetch real-time information about cloud service outages. Configure the API key using an environment variable:

```bash
export PERPLEXITY_API_KEY="your-api-key-here"
```

Or set it when running the server:

```bash
PERPLEXITY_API_KEY="your-api-key-here" python app.py
```

The query asks for:
- Major cloud service outages in the last 2 years
- Financial losses and affected users
- Security breaches and data loss incidents
- Detailed descriptions of each incident

## Development

To run in development mode with auto-reload:

```bash
FLASK_ENV=development python app.py
```

## Production Deployment

For production deployment, use a production-grade WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## CORS Configuration

⚠️ **Security Warning**: The server currently allows CORS from all origins for development convenience. 

**For production deployment**, you MUST restrict CORS to specific domains:

```python
# In app.py, change this line:
CORS(app)

# To:
CORS(app, origins=['https://yourdomain.com', 'https://www.yourdomain.com'])
```

This prevents unauthorized domains from accessing your API.

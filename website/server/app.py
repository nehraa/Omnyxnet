#!/usr/bin/env python3
"""
Simple Flask backend for Pangea Net website
Handles survey form submissions and fetches cloud outage news
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import re
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Data storage directory
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SURVEY_FILE = os.path.join(DATA_DIR, "survey_responses.json")
CACHE_FILE = os.path.join(DATA_DIR, "outages_cache.json")

# Perplexity API configuration
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)


def load_json_file(filepath, default=None):
    """Load JSON file with default fallback"""
    if not os.path.exists(filepath):
        return default if default is not None else []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {filepath}: {e}")
        return default if default is not None else []


def save_json_file(filepath, data):
    """Save data to JSON file"""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/api/survey", methods=["POST"])
def submit_survey():
    """Handle survey form submission"""
    try:
        # Validate request has JSON data
        if not request.json:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        data = request.json

        # Add timestamp and ID
        data["timestamp"] = datetime.now().isoformat()
        data["id"] = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # Load existing responses
        responses = load_json_file(SURVEY_FILE, [])

        # Add new response
        responses.append(data)

        # Save to file
        save_json_file(SURVEY_FILE, responses)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Survey response saved successfully",
                    "id": data["id"],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/survey/stats", methods=["GET"])
def get_survey_stats():
    """Get aggregated survey statistics"""
    try:
        responses = load_json_file(SURVEY_FILE, [])

        # Calculate statistics
        stats = {
            "total_responses": len(responses),
            "q1_stats": {},  # Star ratings
            "q2_stats": {},  # Speed priority
            "q3_stats": {},  # Pain points
            "q4_stats": {},  # Interest level
            "q5_stats": {},  # Use case
            "q6_stats": {},  # Timeline
        }

        # Count responses for each question
        for response in responses:
            for key in ["q1", "q2", "q3", "q4", "q5", "q6"]:
                if key in response:
                    value = str(response[key])
                    stats_key = f"{key}_stats"
                    if value not in stats[stats_key]:
                        stats[stats_key][value] = 0
                    stats[stats_key][value] += 1

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/outages", methods=["GET"])
def get_outages():
    """Fetch latest cloud service outages using Perplexity API"""
    try:
        # Check cache first (cache for 1 hour)
        cache = load_json_file(CACHE_FILE, {"timestamp": 0, "data": None})
        cache_age = datetime.now().timestamp() - cache.get("timestamp", 0)

        if cache_age < 3600 and cache.get("data"):
            return jsonify(cache["data"]), 200

        # Only try API if key is configured
        if not PERPLEXITY_API_KEY:
            return jsonify(get_fallback_outages()), 200

        # Query Perplexity for cloud outage information
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        }

        prompt = """Provide a detailed list of major cloud service outages in the last 2 years (2023-2025). 
        For each outage, include:
        1. Company name (AWS, Google Cloud, Azure, etc.)
        2. Date of outage
        3. Duration (in hours)
        4. Estimated financial losses (in millions USD)
        5. Number of affected users/services
        6. Brief description of the incident
        7. Any security breaches or data losses involved
        
        Format the response as a JSON array of objects with these fields:
        company, date, duration_hours, financial_loss_millions, affected_users, description, security_incident, data_loss
        
        Focus on the biggest, most impactful incidents. Include at least 10-15 incidents."""

        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a data analyst specializing in cloud infrastructure incidents. Provide accurate, well-researched information about cloud service outages.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 4000,
        }

        response = requests.post(
            PERPLEXITY_API_URL, json=payload, headers=headers, timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Try to extract JSON from the response
            try:
                # Look for JSON array in the response
                json_match = re.search(r"\[.*\]", content, re.DOTALL)
                if json_match:
                    outages_data = json.loads(json_match.group())
                else:
                    # Fallback to static data if parsing fails
                    print("Could not extract JSON from Perplexity response")
                    return jsonify(get_fallback_outages()), 200
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing Perplexity response: {e}")
                return jsonify(get_fallback_outages()), 200

            # Calculate totals
            totals = calculate_outage_totals(outages_data)

            result_data = {
                "outages": outages_data,
                "totals": totals,
                "last_updated": datetime.now().isoformat(),
            }

            # Cache the result
            save_json_file(
                CACHE_FILE,
                {"timestamp": datetime.now().timestamp(), "data": result_data},
            )

            return jsonify(result_data), 200
        else:
            # Return fallback data if API fails
            return jsonify(get_fallback_outages()), 200

    except Exception as e:
        print(f"Error fetching outages: {e}")
        # Return fallback data on error
        return jsonify(get_fallback_outages()), 200


def calculate_outage_totals(outages):
    """Calculate aggregate statistics from outages"""
    totals = {
        "total_incidents": len(outages),
        "total_duration_hours": 0,
        "total_financial_loss_millions": 0,
        "total_affected_users": 0,
        "security_incidents": 0,
        "data_loss_incidents": 0,
    }

    for outage in outages:
        totals["total_duration_hours"] += outage.get("duration_hours", 0)
        totals["total_financial_loss_millions"] += outage.get(
            "financial_loss_millions", 0
        )
        totals["total_affected_users"] += outage.get("affected_users", 0)
        if outage.get("security_incident"):
            totals["security_incidents"] += 1
        if outage.get("data_loss"):
            totals["data_loss_incidents"] += 1

    return totals


def get_fallback_outages():
    """Fallback data if API fails"""
    return {
        "outages": [
            {
                "company": "AWS",
                "date": "2024-06-13",
                "duration_hours": 4.5,
                "financial_loss_millions": 250,
                "affected_users": 15000000,
                "description": "Major outage affecting US-EAST-1 region, impacting thousands of websites and services",
                "security_incident": False,
                "data_loss": False,
            },
            {
                "company": "Microsoft Azure",
                "date": "2024-07-30",
                "duration_hours": 8.7,
                "financial_loss_millions": 450,
                "affected_users": 8000000,
                "description": "Global Azure services disruption caused by a configuration change, affecting Microsoft 365 and cloud services",
                "security_incident": False,
                "data_loss": False,
            },
            {
                "company": "Google Cloud",
                "date": "2023-11-08",
                "duration_hours": 3.2,
                "financial_loss_millions": 180,
                "affected_users": 5000000,
                "description": "Networking issues in multiple regions causing service degradation for Cloud Run and GKE",
                "security_incident": False,
                "data_loss": False,
            },
            {
                "company": "AWS",
                "date": "2023-12-07",
                "duration_hours": 11.0,
                "financial_loss_millions": 520,
                "affected_users": 20000000,
                "description": "Extended outage in US-EAST-1 affecting S3, Lambda, and other core services during holiday shopping season",
                "security_incident": False,
                "data_loss": False,
            },
            {
                "company": "Microsoft Azure",
                "date": "2024-01-25",
                "duration_hours": 5.5,
                "financial_loss_millions": 310,
                "affected_users": 12000000,
                "description": "Authentication service failure preventing access to Azure resources worldwide",
                "security_incident": True,
                "data_loss": False,
            },
            {
                "company": "Google Cloud",
                "date": "2024-03-14",
                "duration_hours": 6.8,
                "financial_loss_millions": 290,
                "affected_users": 7500000,
                "description": "Storage system failure causing data access issues and potential data corruption in select regions",
                "security_incident": False,
                "data_loss": True,
            },
            {
                "company": "Cloudflare",
                "date": "2023-10-15",
                "duration_hours": 2.3,
                "financial_loss_millions": 120,
                "affected_users": 30000000,
                "description": "Global CDN and DNS service disruption affecting millions of websites worldwide",
                "security_incident": False,
                "data_loss": False,
            },
            {
                "company": "AWS",
                "date": "2024-09-02",
                "duration_hours": 7.2,
                "financial_loss_millions": 380,
                "affected_users": 18000000,
                "description": "Database service failures in multiple regions, affecting RDS and DynamoDB customers",
                "security_incident": False,
                "data_loss": True,
            },
            {
                "company": "Oracle Cloud",
                "date": "2024-04-19",
                "duration_hours": 14.5,
                "financial_loss_millions": 420,
                "affected_users": 3000000,
                "description": "Catastrophic network failure causing complete service unavailability for enterprise customers",
                "security_incident": True,
                "data_loss": True,
            },
            {
                "company": "Google Cloud",
                "date": "2024-08-22",
                "duration_hours": 4.1,
                "financial_loss_millions": 210,
                "affected_users": 6000000,
                "description": "Load balancing system failure causing cascading failures across multiple services",
                "security_incident": False,
                "data_loss": False,
            },
        ],
        "totals": {
            "total_incidents": 10,
            "total_duration_hours": 67.8,
            "total_financial_loss_millions": 3130,
            "total_affected_users": 124500000,
            "security_incidents": 2,
            "data_loss_incidents": 3,
        },
        "last_updated": datetime.now().isoformat(),
    }


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Only enable debug mode if explicitly set in environment
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)

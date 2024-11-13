
from flask import Flask, request, jsonify
from flask_cors import CORS
from apify_client import ApifyClient
import os
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS
logging.basicConfig(level=logging.DEBUG)

API_TOKEN = os.getenv("API_TOKEN")
API_KEY = os.getenv("MY_API_KEY")

# Function to handle Apify actor calls for new API
def run_apify_actor(urls):
    client = ApifyClient(API_TOKEN)
    run_input = {
        "outputFormat": "captions",
        "urls": urls,
        "maxRetries": 4,
        "proxyOptions": {"useApifyProxy": True},
    }
    actor_id = "1s7eXiaukVuOr4Ueg"
    run = client.actor(actor_id).call(run_input=run_input)
    results = [item for item in client.dataset(run['defaultDatasetId']).iterate_items()]
    return results

# Additional function for handling other APIs
def other_api_logic(data):
    # Placeholder for other API processing logic
    return {"processed_data": data}

@app.route('/api', methods=['POST'])
def api_handler():
    data = request.get_json()
    function_requested = data.get('function')
    app.logger.debug("Function requested: %s", function_requested)

    received_api_key = request.headers.get('Authorization')
    if received_api_key != f'Bearer {API_KEY}':
        app.logger.warning("Unauthorized access attempt with key: %s", received_api_key)
        return jsonify({"error": "Unauthorized"}), 401

    if function_requested == 'run_apify':
        urls = data.get("urls")
        if not urls or not isinstance(urls, list):
            app.logger.error("Missing 'urls' in request or 'urls' is not a list")
            return jsonify({"error": "Missing 'urls' in request or 'urls' is not a list"}), 400
        results = run_apify_actor(urls)
        return jsonify({"status": "success", "data": results})

    elif function_requested == 'other_api':
        processed_data = other_api_logic(data)
        return jsonify(processed_data)

    else:
        app.logger.error("Unsupported function: %s", function_requested)
        return jsonify({"error": "Function not supported"}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

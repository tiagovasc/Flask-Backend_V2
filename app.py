from flask import Flask, request, jsonify
from flask_cors import CORS
from apify_client import ApifyClient
import os
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS

logging.basicConfig(level=logging.DEBUG)  # Set logging to debug for detailed output

API_TOKEN = os.getenv("API_TOKEN")
API_KEY = os.getenv("MY_API_KEY")

@app.route('/run', methods=['POST'])
def run_actor():
    app.logger.debug("Received headers: %s", request.headers)
    received_api_key = request.headers.get('Authorization')
    if received_api_key != f'Bearer {API_KEY}':
        app.logger.warning("Unauthorized access attempt with key: %s", received_api_key)
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    app.logger.debug("Received data: %s", data)

    urls = data.get("urls")
    if not urls or not isinstance(urls, list):
        app.logger.error("Missing 'urls' in request or 'urls' is not a list")
        return jsonify({"error": "Missing 'urls' in request or 'urls' is not a list"}), 400

    client = ApifyClient(API_TOKEN)
    run_input = {
        "urls": urls,
        "maxRetries": 3,
        "proxyOptions": {"useApifyProxy": True},
    }
    run = client.actor("karamelo/test-youtube-structured-transcript-extractor").call(run_input=run_input)
    results = [item['captions'] for item in client.dataset(run["defaultDatasetId"]).iterate_items()]
    app.logger.debug("Actor results: %s", results)

    return jsonify({"status": "success", "data": results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Ensure the app runs on the correct host and port

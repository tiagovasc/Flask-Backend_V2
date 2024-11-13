from flask import Flask, request, jsonify
from flask_cors import CORS
from apify_client import ApifyClient
import os
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS

# Set up comprehensive logging
logging.basicConfig(level=logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s [%(name)s] %(message)s'
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

API_TOKEN = os.getenv("API_TOKEN") 
API_KEY = os.getenv("MY_API_KEY") 

# Function to handle Apify actor calls for new API
def run_apify_actor(urls):
    app.logger.debug("Starting Apify actor for URLs: %s", urls)
    client = ApifyClient(API_TOKEN)
    run_input = {
        "outputFormat": "captions",
        "urls": urls,
        "maxRetries": 4,
        "proxyOptions": {"useApifyProxy": True},
    }
    actor_id = "1s7eXiaukVuOr4Ueg"
    app.logger.debug("Running Apify actor with input: %s", run_input)
    run = client.actor(actor_id).call(run_input=run_input)
    app.logger.debug("Apify actor run details: %s", run)

    # Fetch results from the Apify dataset
    results = [item for item in client.dataset(run['defaultDatasetId']).iterate_items()]
    app.logger.debug("Fetched results from Apify dataset: %s", results)
    
    # Process results to map URLs to transcripts
    url_transcript_map = {}
    for item in results:
        app.logger.debug("Processing item: %s", item)
        # Attempt to get the 'url' from the item
        url = item.get('url')
        if not url:
            video_id = item.get('videoId')
            if video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
                app.logger.debug("Constructed URL from videoId: %s", url)
            else:
                app.logger.warning("Item without 'url' or 'videoId': %s", item)
                continue
        captions = item.get('captions', [])
        transcript = ' '.join(captions)
        url_transcript_map[url] = transcript
        app.logger.debug("Added transcript for URL %s", url)
    return url_transcript_map

# Additional function for handling other APIs
def other_api_logic(data):
    # Placeholder for other API processing logic
    app.logger.debug("Processing other API logic with data: %s", data)
    return {"processed_data": data}

@app.route('/api', methods=['POST'])
def api_handler():
    app.logger.debug("Received request with headers: %s", dict(request.headers))
    data = request.get_json()
    app.logger.debug("Received data: %s", data)
    function_requested = data.get('function')
    app.logger.debug("Function requested: %s", function_requested)

    received_api_key = request.headers.get('Authorization')
    if received_api_key != f'Bearer {API_KEY}':
        app.logger.warning("Unauthorized access attempt with key: %s", received_api_key)
        return jsonify({"error": "Unauthorized"}), 401

    if function_requested == 'run_apify':
        urls = data.get("urls")
        app.logger.debug("URLs received: %s", urls)
        if not urls or not isinstance(urls, list):
            app.logger.error("Missing 'urls' in request or 'urls' is not a list")
            return jsonify({"error": "Missing 'urls' in request or 'urls' is not a list"}), 400
        try:
            results = run_apify_actor(urls)
            app.logger.debug("Returning results: %s", results)
            return jsonify({"status": "success", "data": results})
        except Exception as e:
            app.logger.exception("An error occurred while processing 'run_apify'")
            return jsonify({"error": "An error occurred", "details": str(e)}), 500

    elif function_requested == 'other_api':
        processed_data = other_api_logic(data)
        app.logger.debug("Returning processed data: %s", processed_data)
        return jsonify(processed_data)

    else:
        app.logger.error("Unsupported function: %s", function_requested)
        return jsonify({"error": "Function not supported"}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

from flask import Flask, request, jsonify
from flask_cors import CORS
from apify_client import ApifyClient
import os
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS

# Set up simplified logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s [%(name)s] %(message)s')

API_TOKEN = os.getenv("API_TOKEN")
API_KEY = os.getenv("MY_API_KEY")

# Function to handle Apify actor calls for new API
def run_apify_actor(urls):
    app.logger.debug(f"Starting Apify actor for URLs: {urls}")
    client = ApifyClient(API_TOKEN)
    run_input = {
        "outputFormat": "captions",
        "urls": urls,
        "maxRetries": 4,
        "proxyOptions": {"useApifyProxy": True},
    }
    actor_id = "1s7eXiaukVuOr4Ueg"
    app.logger.debug("Running Apify actor...")
    run = client.actor(actor_id).call(run_input=run_input)
    app.logger.debug(f"Apify actor run completed with status: {run.get('status')}")

    # Fetch results from the Apify dataset
    results = [item for item in client.dataset(run['defaultDatasetId']).iterate_items()]
    app.logger.debug(f"Fetched {len(results)} result(s) from Apify dataset.")

    # Process results to map URLs to transcripts
    url_transcript_map = {}
    for item in results:
        # Attempt to get the 'url' from the item
        url = item.get('url')
        if not url:
            video_id = item.get('videoId')
            if video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                app.logger.warning(f"Item without 'url' or 'videoId': {item}")
                continue
        captions = item.get('captions', [])
        transcript = ' '.join(captions)
        url_transcript_map[url] = transcript
        # Log the transcript once per video
        app.logger.debug(f"Transcript for {url}:\n{transcript}\n")
    return url_transcript_map

@app.route('/api', methods=['POST'])
def api_handler():
    data = request.get_json()
    function_requested = data.get('function')
    urls = data.get("urls")
    app.logger.debug(f"Received request for function '{function_requested}' with URLs: {urls}")

    received_api_key = request.headers.get('Authorization')
    if received_api_key != f'Bearer {API_KEY}':
        app.logger.warning("Unauthorized access attempt.")
        return jsonify({"error": "Unauthorized"}), 401

    if function_requested == 'run_apify':
        if not urls or not isinstance(urls, list):
            app.logger.error("Missing 'urls' in request or 'urls' is not a list.")
            return jsonify({"error": "Missing 'urls' in request or 'urls' is not a list"}), 400
        try:
            results = run_apify_actor(urls)
            app.logger.debug(f"Returning transcripts for URLs: {list(results.keys())}")
            return jsonify({"status": "success", "data": results})
        except Exception as e:
            app.logger.exception("An error occurred while processing 'run_apify'.")
            return jsonify({"error": "An error occurred", "details": str(e)}), 500

    else:
        app.logger.error(f"Unsupported function requested: {function_requested}")
        return jsonify({"error": "Function not supported"}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

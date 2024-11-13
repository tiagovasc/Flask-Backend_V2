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
    '%(asctime)s %(levelname)s [%(name)s] URL: %(url)s Message: %(message)s'
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

API_TOKEN = os.getenv("API_TOKEN") 
API_KEY = os.getenv("MY_API_KEY") 

# Function to handle Apify actor calls for new API
def run_apify_actor(urls):
    app.logger.debug({"url": "N/A", "message": "Starting Apify actor for URLs", "urls": urls})
    client = ApifyClient(API_TOKEN)
    run_input = {
        "outputFormat": "captions",
        "urls": urls,
        "maxRetries": 4,
        "proxyOptions": {"useApifyProxy": True},
    }
    actor_id = "1s7eXiaukVuOr4Ueg"
    run = client.actor(actor_id).call(run_input=run_input)
    app.logger.debug({"url": "N/A", "message": "Apify actor run details", "details": run})

    # Fetch results from the Apify dataset
    results = [item for item in client.dataset(run['defaultDatasetId']).iterate_items()]
    url_transcript_map = {}
    for item in results:
        video_id = item.get('videoId')
        url = f"https://www.youtube.com/watch?v={video_id}" if video_id else "Unknown URL"
        app.logger.debug({"url": url, "message": "Processing item"})
        captions = item.get('captions', [])
        transcript = ' '.join(captions)
        url_transcript_map[url] = transcript
        app.logger.debug({"url": url, "message": "Transcript processed and stored"})

    # Only log the complete results dictionary if necessary for troubleshooting
    app.logger.debug({"url": "N/A", "message": "All URLs processed, transcripts stored."})
    return url_transcript_map

@app.route('/api', methods=['POST'])
def api_handler():
    received_headers = dict(request.headers)
    app.logger.debug({"url": "N/A", "message": "Received request", "headers": received_headers})
    data = request.get_json()
    function_requested = data.get('function')
    app.logger.debug({"url": "N/A", "message": "Function requested", "function": function_requested})

    received_api_key = received_headers.get('Authorization')
    if received_api_key != f'Bearer {API_KEY}':
        app.logger.warning({"url": "N/A", "message": "Unauthorized access attempt", "key": received_api_key})
        return jsonify({"error": "Unauthorized"}), 401

    if function_requested == 'run_apify':
        urls = data.get("urls")
        app.logger.debug({"url": "N/A", "message": "URLs received", "urls": urls})
        if not urls or not isinstance(urls, list):
            app.logger.error({"url": "N/A", "message": "Missing 'urls' in request or 'urls' is not a list"})
            return jsonify({"error": "Missing 'urls' in request or 'urls' is not a list"}), 400
        try:
            results = run_apify_actor(urls)
            app.logger.debug({"url": "N/A", "message": "Returning results", "urls_processed": list(results.keys())})
            return jsonify({"status": "success", "data": results})
        except Exception as e:
            app.logger.exception({"url": "N/A", "message": "An error occurred while processing 'run_apify'", "exception": str(e)})
            return jsonify({"error": "An error occurred", "details": str(e)}), 500

    else:
        app.logger.error({"url": "N/A", "message": "Unsupported function requested", "function": function_requested})
        return jsonify({"error": "Function not supported"}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

from flask import Flask, request, jsonify
from flask_cors import CORS
from apify_client import ApifyClient
import os
import logging
import traceback

app = Flask(__name__)

# Configure CORS to allow requests from any origin (adjust in production)
CORS(app, resources={r"/api": {"origins": "*"}})

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s [%(name)s] %(message)s')

# Set app logger to DEBUG level
app.logger.setLevel(logging.DEBUG)

# Suppress debug logging from other modules
for logger_name in ('httpx', 'httpcore', 'apify_client'):
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Retrieve environment variables
API_TOKEN = os.getenv("API_TOKEN")
API_KEY = os.getenv("MY_API_KEY")

if not API_TOKEN or not API_KEY:
    app.logger.error("API_TOKEN or MY_API_KEY environment variables not set.")
    # Optionally, raise an exception or exit if these are critical

# Function to handle Apify actor calls
def run_apify_actor(urls):
    app.logger.debug(f"run_apify_actor started for URLs: {urls}")
    client = ApifyClient(API_TOKEN)
    run_input = {
        "outputFormat": "captions",
        "urls": urls,
        "maxRetries": 4,
        "proxyOptions": {"useApifyProxy": True},
    }
    actor_id = "1s7eXiaukVuOr4Ueg"
    try:
        app.logger.debug(f"Calling Apify actor '{actor_id}' with input: {run_input}")
        run = client.actor(actor_id).call(run_input=run_input)
        status = run.get('status')
        app.logger.debug(f"Apify actor run status: {status}")

        if status != 'SUCCEEDED':
            error_msg = f"Apify actor failed with status: {status}"
            app.logger.error(error_msg)
            return {}, error_msg

        dataset_id = run.get('defaultDatasetId')
        if not dataset_id:
            error_msg = "No dataset ID found in Apify run result."
            app.logger.error(error_msg)
            return {}, error_msg

        app.logger.debug(f"Fetching results from dataset ID: {dataset_id}")
        results = [item for item in client.dataset(dataset_id).iterate_items()]
        app.logger.debug(f"Fetched {len(results)} result(s) from dataset.")

        url_transcript_map = {}
        for item in results:
            url = item.get('url') or f"https://www.youtube.com/watch?v={item.get('videoId')}"
            if not url:
                app.logger.warning(f"Item missing 'url' and 'videoId': {item}")
                continue
            captions = item.get('captions', [])
            transcript = ' '.join(captions)
            url_transcript_map[url] = transcript

            # Log concise transcript info
            transcript_preview = transcript[:75].replace('\n', ' ') + '...'
            app.logger.info(f"Transcript for {url}: {transcript_preview}")
        return url_transcript_map, None
    except Exception as e:
        error_details = traceback.format_exc()
        app.logger.error(f"Exception in run_apify_actor: {e}")
        app.logger.debug(f"Stack trace: {error_details}")
        return {}, f"Exception in run_apify_actor: {e}"

@app.route('/api', methods=['POST'])
def api_handler():
    try:
        data = request.get_json()
        function_requested = data.get('function')
        urls = data.get("urls")
        app.logger.debug(f"Received request: function='{function_requested}', URLs={urls}")

        received_api_key = request.headers.get('Authorization')
        if received_api_key != f'Bearer {API_KEY}':
            app.logger.warning("Unauthorized access attempt.")
            return jsonify({"error": "Unauthorized"}), 401

        if function_requested == 'run_apify':
            if not urls or not isinstance(urls, list):
                error_msg = "Invalid 'urls' in request; expected a list of URLs."
                app.logger.error(error_msg)
                return jsonify({"error": error_msg}), 400

            app.logger.debug(f"Processing 'run_apify' for URLs: {urls}")
            results, error_message = run_apify_actor(urls)
            if error_message:
                app.logger.error(f"Error in run_apify_actor: {error_message}")
                return jsonify({"error": error_message}), 500

            app.logger.debug(f"Transcripts obtained for URLs: {list(results.keys())}")
            return jsonify({"status": "success", "data": results})

        else:
            error_msg = f"Unsupported function requested: {function_requested}"
            app.logger.error(error_msg)
            return jsonify({"error": error_msg}), 400

    except Exception as e:
        error_details = traceback.format_exc()
        app.logger.error(f"Exception in api_handler: {e}")
        app.logger.debug(f"Stack trace: {error_details}")
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

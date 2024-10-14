import os
import sys
import logging
from flask import Flask, render_template, request, jsonify
import vertexai  # type: ignore
import markdown  # type: ignore
from vertexai.generative_models import GenerativeModel  # type: ignore
from vertexai.preview.generative_models import HarmBlockThreshold  # type: ignore
import vertexai.preview.generative_models as generative_models  # type: ignore

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)

# Check and set required environment variables
required_vars = ['PROJECT_ID', 'REGION', 'MODEL_NAME', 'MODERATION_LEVEL']
for var in required_vars:
    if not os.getenv(var):
        logging.error("environment variable '%s' is not set", var)
        sys.exit(1)

PROJECT_ID = os.getenv('PROJECT_ID')
REGION = os.getenv('REGION')
MODEL_NAME = os.getenv('MODEL_NAME')
MODERATION_LEVEL = os.getenv('MODERATION_LEVEL', 'moderate')

app = Flask(__name__)

vertexai.init(project=PROJECT_ID, location=REGION)

model = GenerativeModel(MODEL_NAME)

generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}


def get_safety_settings(content_filter_strength):
    thresholds = {
        "strict": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        "moderate": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        "relaxed": HarmBlockThreshold.BLOCK_ONLY_HIGH,
        "minimal": HarmBlockThreshold.BLOCK_NONE
    }
    threshold = thresholds.get(content_filter_strength, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
    logging.info("Using content filter strength: %s", content_filter_strength)

    return {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: threshold,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: threshold,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: threshold,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: threshold,
    }


def generate_content(prompt, content_filter_strength="moderate"):
    safety_settings = get_safety_settings(content_filter_strength)
    response = model.generate_content(
        prompt,
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    return response.text


@app.route("/", methods=["GET", "POST"])
def index():
    response_text = ""
    if request.method == "POST" or (request.method == "GET" and request.args.get("prompt")):
        prompt = request.form.get("prompt") or request.args.get("prompt")
        moderation_level = request.form.get("moderation_level") or request.args.get(
            "moderation_level", MODERATION_LEVEL
        )
        response_text = generate_content(
            prompt, content_filter_strength=moderation_level
        )

        if request.headers.get('Accept') == 'application/json' or request.args.get("format") == "json":
            return jsonify({"response": response_text})
        else:
            response_text = markdown.markdown(response_text)
            return render_template("index-with-css.html", response_text=response_text)
    else:
        return render_template("index-with-css.html", response_text="")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)

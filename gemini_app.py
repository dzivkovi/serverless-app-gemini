"""
Generate content using the provided prompt and moderation level.
"""
import os
import sys
import logging
from flask import Flask, render_template, request, jsonify, session
import vertexai  # type: ignore
import markdown  # type: ignore
from vertexai.generative_models import GenerativeModel  # type: ignore
from vertexai.preview.generative_models import HarmBlockThreshold  # type: ignore
import vertexai.preview.generative_models as generative_models  # type: ignore
from vertexai.preview.generative_models import GenerationConfig


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
        logging.error("Environment variable '%s' is not set", var)
        sys.exit(1)

PROJECT_ID = os.getenv('PROJECT_ID')
REGION = os.getenv('REGION')
MODEL_NAME = os.getenv('MODEL_NAME')
MODERATION_LEVEL = os.getenv('MODERATION_LEVEL', 'moderate')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())  # Enable session management


try:
    vertexai.init(project=PROJECT_ID, location=REGION)
    model = GenerativeModel(MODEL_NAME)
    logging.info("Vertexai initialized successfully")
except Exception as e:
    logging.error("Failed to initialize Vertexai: %s", e)
    sys.exit(1)

generation_config = GenerationConfig(
    max_output_tokens=8192,
    temperature=1,
    top_p=0.95,
)


def get_safety_settings(content_filter_strength):
    """
    Get the safety settings based on the content filter strength.
    Possible values are: strict, moderate, relaxed, minimal
    """
    thresholds = {
        "strict": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        "moderate": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        "relaxed": HarmBlockThreshold.BLOCK_ONLY_HIGH,
        "minimal": HarmBlockThreshold.BLOCK_NONE
    }
    threshold = thresholds.get(content_filter_strength, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
    logging.info("Content filter set to: '%s'", content_filter_strength)

    return {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: threshold,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: threshold,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: threshold,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: threshold,
    }


def generate_content(prompt, content_filter_strength="moderate"):
    """
    Generate content using the provided prompt.

    Args:
        prompt (str): The input prompt for content generation.
        content_filter_strength (str, optional): Moderation level. Defaults to "moderate".

    Returns:
        tuple: (generated_text, is_moderated, moderation_reason)

    Raises:
        Exception: If there's an error during content generation.
    """
    logging.debug("Sent to Gemini: %s", prompt)
    safety_settings = get_safety_settings(content_filter_strength)

    try:
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        # Log full response for debugging
        logging.debug("Gemini response: %s", response)

        if response.candidates:
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, 'finish_reason', 'Unknown')
            logging.info("Finish Reason: %s", finish_reason)

            # Map safety ratings to more descriptive labels
            safety_levels = {1: "Low", 2: "Medium", 3: "High", 4: "Very High"}

            logging.info("Safety Ratings:")
            safety_info = []
            for rating in candidate.safety_ratings:
                category = getattr(rating, 'category', 'Unknown')
                probability = getattr(rating, 'probability', 'Unknown')
                level = safety_levels.get(probability, "Unknown")
                logging.info(f"  {category}: {level} ({probability})")
                safety_info.append(f"{category}: {level}")

            if finish_reason == "SAFETY":
                logging.warning("Content generation stopped due to safety concerns.")
                return None, True, "Content blocked due to safety concerns", safety_info

            if hasattr(candidate, 'content') and candidate.content.parts:
                generated_text = candidate.content.parts[0].text
                logging.debug("Received from Gemini: %s", generated_text)
                return generated_text, False, None, safety_info
            else:
                logging.warning("No content generated.")
                return None, False, "No content generated", safety_info
        else:
            logging.warning("No candidates in the response.")
            return None, False, "No candidates in the response", []

    except Exception as e:
        logging.error("Error generating content: %s", str(e))
        raise


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Render the index page when a GET request is received.
    POST request can return JSON response, if the Accept header is set to 'application/json'.
    """
    if request.method == "POST":
        prompt = request.form.get("prompt")
        moderation_level = request.form.get("moderation_level", MODERATION_LEVEL)

        # Store the prompt in the session
        session['last_prompt'] = prompt
        session['last_moderation_level'] = moderation_level

        try:
            response_text, is_moderated, moderation_reason, safety_info = (
                generate_content(prompt, content_filter_strength=moderation_level)
            )

            if is_moderated:
                if request.headers.get('Accept') == 'application/json':
                    return (
                        jsonify(
                            {
                                "error": "Content moderated",
                                "reason": moderation_reason,
                                "safety_info": safety_info,
                            }
                        ),
                        403,
                    )
                else:
                    return render_template("index-with-css.html",
                                           response_text=f"Content moderated: {moderation_reason}",
                                           safety_info=safety_info,
                                           last_prompt=prompt,
                                           last_moderation_level=moderation_level)

            if response_text:
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({"response": response_text, "safety_info": safety_info})
                else:
                    response_text = markdown.markdown(response_text)
                    return render_template("index-with-css.html",
                                           response_text=response_text,
                                           safety_info=safety_info,
                                           last_prompt=prompt,
                                           last_moderation_level=moderation_level)
            else:
                error_message = "No content generated"
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({"error": error_message, "safety_info": safety_info}), 404
                else:
                    return render_template("index-with-css.html",
                                           response_text=f"Error: {error_message}",
                                           safety_info=safety_info,
                                           last_prompt=prompt,
                                           last_moderation_level=moderation_level)

        except Exception as e:
            error_message = str(e)
            logging.error("Gemini AI error: %s", error_message)
            if request.headers.get('Accept') == 'application/json':
                return jsonify({"error": error_message}), 500
            else:
                return render_template("index-with-css.html",
                                       response_text=f"Error: {error_message}",
                                       last_prompt=prompt,
                                       last_moderation_level=moderation_level)
    else:  # GET request
        # Retrieve the last prompt and moderation level from the session
        last_prompt = session.get('last_prompt', '')
        last_moderation_level = session.get('last_moderation_level', MODERATION_LEVEL)
        return render_template("index-with-css.html",
                               response_text="",
                               last_prompt=last_prompt,
                               last_moderation_level=last_moderation_level)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)

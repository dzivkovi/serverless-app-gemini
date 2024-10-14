# Google Gemini with built-in Content Moderation

This Serverless App demonstrates the content moderation capabilities of Google Gemini AI models. The app uses a Flask server to accept text input and return Gemini-generated responses, showcasing how AI can be both powerful and responsible through built-in safeguards against inappropriate content.

## Overview

Gemini's content moderation system is designed to handle a wide range of sensitive topics, including:

* Hate speech and discrimination
* Violence and graphic content
* Sexually explicit material
* Spam and misleading information
* Personal information and privacy violations

When users input prompts related to these sensitive areas, the model responds with appropriate, family-friendly content or politely declines to generate material that could be harmful or offensive. This demonstrates AI's capacity to engage in diverse conversations while maintaining ethical boundaries.

For example, if a user requests content related to explicit sexual topics or violent scenarios, Gemini will steer the conversation towards more appropriate subjects or provide educational responses about the importance of respectful communication.

The project leverages [Vertex AI's safety filters](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/configure-safety-filters), allowing fine-tuned control over content generation.

## Installation

The project includes a Dockerfile for containerization and a Cloud Build configuration for automated builds and deployments to Cloud Run, making it easy to deploy and scale.

### Prerequisites

* Google Cloud account
* `gcloud` CLI installed and configured
* Python 3.9+

### Setup

1. Clone the repository:

   ```sh
   git clone <repository-url>
   cd serverless-app-gemini
   ```

2. Set up environment variables:

   ```sh
   cp env.sample .env
   ```

   Edit `.env` and fill in your `PROJECT_ID`, `REGION`, and other required values.

3. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

### Local Testing

To test the app locally:

1. Set environment variables:

   ```sh
   export $(grep -v '^#' .env | xargs -d '\n')
   ```

2. Run the Flask app:

   ```sh
   python gemini-app.py
   ```

3. Test using curl:

   ```sh
   curl -X POST -H "Accept: application/json" -d "prompt=Tell me a short love scene, without being too graphic&moderation_level=strict" http://localhost:8080

   curl "http://localhost:8080/?prompt=Sexy%20story,%20please&moderation_level=relaxed&format=json"

   ```

### Deployment

1. Set up project and app name:

   ```sh
   export PROJECT_ID=$(gcloud config get-value project)
   export REGION=$(gcloud config get-value run/region)
   export APP_NAME=$(basename $(pwd))
   ```

2. Build and submit the container:

   ```sh
   gcloud builds submit --config cloudbuild.yaml .
   ```

3. Deploy to Cloud Run:

   ```sh
   gcloud run deploy $APP_NAME \
     --image gcr.io/$PROJECT_ID/serverless-app-gemini \
     --region $REGION \
     --allow-unauthenticated \
     --set-env-vars=PROJECT_ID=$PROJECT_ID,REGION=$REGION
   ```

   Note: The `--allow-unauthenticated` flag allows public access to your app. Use this only if you want your app to be publicly accessible.

4. Get the app URL:

   ```sh
   export APP_URL=$(gcloud run services describe $APP_NAME --region $REGION --format='value(status.url)')
   echo $APP_URL
   ```

5. Test your deployed app:

   ```sh
   curl -X POST -d "prompt=Tell me about content moderation" $APP_URL
   ```

## Notes

* This project uses Cloud Build and Cloud Run directly, without local Docker builds.
* Ensure all necessary APIs are enabled in your Google Cloud project.
* Remember to set up proper authentication and permissions for Gemini API access.
* The app is deployed with public access (`--allow-unauthenticated`). For production environments, consider implementing appropriate authentication mechanisms.

## Credits

This project is a fork of the original work presented in the article [Leveraging Serverless App Deployment with Cloud Run and Gemini: A Beginner's Guide](https://medium.com/google-cloud/leveraging-serverless-app-deployment-with-cloud-run-and-gemini-a-beginners-guide-8589705e1e7c), extended to highlight Gemini's content moderation features.

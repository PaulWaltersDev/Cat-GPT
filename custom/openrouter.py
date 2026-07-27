import os, dotenv
from openai import OpenAI
from deepeval.models import OpenRouterModel

dotenv.load_dotenv()  # Load environment variables from .env file

def get_model():
    model = OpenRouterModel(
        model="anthropic/claude-sonnet-4.6",
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL")
    )
    return model
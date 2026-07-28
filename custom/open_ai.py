import os, dotenv
from deepeval.models import GPTModel

dotenv.load_dotenv()  # Load environment variables from .env file

# For all providers and models that have GPT-compatible APIs
def get_model():
    model = GPTModel(
        model=os.getenv("DEEPEVAL_MODEL"),
        api_key=os.getenv("DEEPEVAL_API_KEY"),
        base_url=os.getenv("DEEPEVAL_OPENAI_URL")
    )
    return model
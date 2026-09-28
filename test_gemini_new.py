import yaml
from google import genai

with open("config/config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

api_key = cfg["api_keys"]["gemini"]
client = genai.Client(api_key=api_key)

print("--- Testing with gemini-3.6-flash ---")
try:
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Say Hello and generate 1 fun fact about space in 1 sentence."
    )
    print("Gemini Response:\n", response.text)
except Exception as e:
    print("Error with gemini-3.6-flash:", e)

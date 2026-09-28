import yaml
import requests
import google.generativeai as genai

with open("config/config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

print("--- Testing Gemini API ---")
try:
    genai.configure(api_key=cfg["api_keys"]["gemini"])
    model = genai.GenerativeModel("gemini-1.5-flash")
    res = model.generate_content("Say OK")
    print("Gemini API: SUCCESS ->", res.text.strip())
except Exception as e:
    print("Gemini API Error:", e)

print("\n--- Testing Pexels API ---")
try:
    headers = {"Authorization": cfg["api_keys"]["pexels"]}
    r = requests.get("https://api.pexels.com/videos/search", headers=headers, params={"query": "space", "per_page": 1})
    if r.status_code == 200:
        data = r.json()
        print(f"Pexels API: SUCCESS -> Found {len(data.get('videos', []))} video(s)")
    else:
        print("Pexels API Failed, status:", r.status_code, r.text)
except Exception as e:
    print("Pexels API Error:", e)

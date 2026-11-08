import urllib.request
import json

payload = {
    "answer": (
        "OpenAI GPT-4 pricing starts at $30.00 per million prompt tokens and $60.00 per million completion tokens. "
        "In comparison, Anthropic Claude 3 Opus costs $15.00 per 1M input tokens and $75.00 per 1M output tokens. "
        "Furthermore, GPT-3.5-Turbo remains the most cost-effective OpenAI model for lightweight tasks at $0.50 per million input tokens."
    ),
    "options": {
        "rewrite": True,
    }
}

req = urllib.request.Request(
    "http://localhost:8000/api/verify",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print("STATUS: SUCCESS")
        print(f"Overall Freshness: {data.get('overall_freshness')}")
        print(f"Total Claims: {len(data.get('results', []))}")
        for r in data.get("results", []):
            print(f"[{r.get('verdict').upper()}] {r.get('claim', {}).get('entity')} -> Score: {r.get('freshness_score')}%")
            print(f"   Best Before: {r.get('best_before_date')}")
            print(f"   Current Value: {r.get('current_value')}")
            print(f"   Explanation: {r.get('explanation')[:100]}...")
        if data.get("corrected_answer"):
            print("\nCorrected Answer:\n", data.get("corrected_answer"))
except Exception as e:
    print("ERROR:", e)

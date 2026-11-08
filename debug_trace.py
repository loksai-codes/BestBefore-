import sys, os
sys.path.insert(0, os.path.abspath("."))
import asyncio
from app.pipeline.orchestrator import run_pipeline
from app.models.api import VerifyOptions

async def test():
    try:
        res = await run_pipeline(
            answer=(
                "OpenAI GPT-4 pricing starts at $30.00 per million prompt tokens and $60.00 per million completion tokens. "
                "In comparison, Anthropic Claude 3 Opus costs $15.00 per 1M input tokens and $75.00 per 1M output tokens. "
                "Furthermore, GPT-3.5-Turbo remains the most cost-effective OpenAI model for lightweight tasks at $0.50 per million input tokens."
            ),
            options=VerifyOptions(rewrite=False)
        )
        print("Done:", len(res.results))
        for r in res.results:
            print(r.verdict, r.explanation)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())

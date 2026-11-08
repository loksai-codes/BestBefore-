"""Recorded Tavily Search and Extract fixtures for 3 distinct claim types:
1. Pricing (OpenAI GPT-4 API pricing)
2. Leadership (Starbucks CEO)
3. Regulation (FTC Non-Compete nationwide injunction)
"""

FIXTURE_PRICING_SEARCH = {
    "results": [
        {
            "url": "https://openai.com/api/pricing/",
            "title": "OpenAI API Pricing & Models",
            "content": "GPT-4o is our flagship model, costing $2.50 per 1M input tokens and $10.00 per 1M output tokens. Legacy GPT-4 base models are priced at lower rates with GPT-4 Turbo.",
            "published_date": "2024-10-01",
            "score": 0.98,
        },
        {
            "url": "https://techcrunch.com/2024/05/13/openai-launches-gpt-4o/",
            "title": "OpenAI launches GPT-4o with significant price cuts",
            "content": "OpenAI introduced GPT-4o with half the cost of GPT-4 Turbo, rendering previous $30 per million rates obsolete.",
            "published_date": "2024-05-13",
            "score": 0.92,
        },
    ]
}

FIXTURE_PRICING_EXTRACT = {
    "results": [
        {
            "url": "https://openai.com/api/pricing/",
            "raw_content": "# OpenAI API Pricing\n\nGPT-4o: $2.50 / 1M input tokens, $10.00 / 1M output tokens.\nGPT-4o mini: $0.15 / 1M input tokens, $0.60 / 1M output tokens.\nPrevious GPT-4 rates of $30/$60 are superseded.",
        }
    ]
}

FIXTURE_LEADERSHIP_SEARCH = {
    "results": [
        {
            "url": "https://stories.starbucks.com/press/2024/starbucks-names-brian-niccol-as-chairman-and-ceo/",
            "title": "Starbucks Names Brian Niccol as Chairman and CEO",
            "content": "Starbucks Corporation announced that Brian Niccol has been appointed Chairman and Chief Executive Officer, effective September 9, 2024, replacing Laxman Narasimhan.",
            "published_date": "2024-08-13",
            "score": 0.99,
        },
        {
            "url": "https://www.reuters.com/business/retail-consumer/starbucks-replaces-ceo-narasimhan-with-chipotle-head-niccol-2024-08-13/",
            "title": "Starbucks replaces CEO Narasimhan with Chipotle head Niccol",
            "content": "Starbucks replaced Laxman Narasimhan with Brian Niccol after activist investor pressure.",
            "published_date": "2024-08-13",
            "score": 0.95,
        },
    ]
}

FIXTURE_LEADERSHIP_EXTRACT = {
    "results": [
        {
            "url": "https://stories.starbucks.com/press/2024/starbucks-names-brian-niccol-as-chairman-and-ceo/",
            "raw_content": "Brian Niccol took office as Chief Executive Officer and Chairman of the Board of Starbucks on September 9, 2024. Laxman Narasimhan is no longer CEO.",
        }
    ]
}

FIXTURE_REGULATION_SEARCH = {
    "results": [
        {
            "url": "https://www.ftc.gov/news-events/news/press-releases/2024/04/ftc-announces-rule-banning-noncompetes",
            "title": "FTC Non-Compete Clause Rule Proceedings",
            "content": "Update: On August 20, 2024, the U.S. District Court for the Northern District of Texas set aside the FTC Non-Compete Rule nationwide in Ryan LLC v. FTC.",
            "published_date": "2024-08-21",
            "score": 0.99,
        },
        {
            "url": "https://www.reuters.com/legal/us-judge-blocks-ftc-ban-worker-noncompete-agreements-2024-08-20/",
            "title": "US judge blocks FTC ban on worker noncompete agreements",
            "content": "A federal judge in Texas blocked the FTC from enforcing a rule banning worker noncompetes, ruling the agency lacked statutory authority.",
            "published_date": "2024-08-20",
            "score": 0.96,
        },
    ]
}

FIXTURE_REGULATION_EXTRACT = {
    "results": [
        {
            "url": "https://www.ftc.gov/news-events/news/press-releases/2024/04/ftc-announces-rule-banning-noncompetes",
            "raw_content": "The FTC Non-Compete Rule was enjoined and set aside nationwide on August 20, 2024. It did not take effect on September 4, 2024.",
        }
    ]
}

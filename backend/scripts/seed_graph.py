"""Seeds the FalkorDB Cloud graph with historical facts for the demo timeline UI.
Idempotent: uses MERGE so repeated executions do not create duplicate nodes.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.graph.client import GraphStore

HISTORICAL_SEEDS = [
    {
        "entity_name": "OpenAI GPT-4",
        "norm_entity": "openai gpt-4",
        "attr_name": "pricing",
        "historical": {
            "id": "seed-fact-gpt4-pricing-old",
            "value": "$30.00 / 1M prompt, $60.00 / 1M completion",
            "valid_from": "2023-03-14T00:00:00Z",
            "valid_to": "2024-05-13T17:00:00Z",
            "recorded_at": "2023-03-14T00:00:00Z",
            "superseded_at": "2024-05-13T17:00:00Z",
            "source_url": "https://openai.com/api/pricing/",
            "authority": "official",
        },
        "current": {
            "id": "seed-fact-gpt4-pricing-cur",
            "value": "GPT-4o at $2.50 / 1M prompt, $10.00 / 1M completion",
            "valid_from": "2024-05-13T17:00:00Z",
            "valid_to": None,
            "recorded_at": "2024-05-13T17:00:00Z",
            "superseded_at": None,
            "source_url": "https://openai.com/api/pricing/",
            "authority": "official",
        },
        "verification": {
            "id": "seed-verif-gpt4-pricing",
            "verdict": "outdated",
            "freshness_score": 25,
            "verified_at": "2024-10-15T12:00:00Z",
        },
    },
    {
        "entity_name": "Starbucks",
        "norm_entity": "starbucks",
        "attr_name": "ceo",
        "historical": {
            "id": "seed-fact-sbux-ceo-old",
            "value": "Laxman Narasimhan",
            "valid_from": "2023-03-23T00:00:00Z",
            "valid_to": "2024-08-13T12:00:00Z",
            "recorded_at": "2023-03-23T00:00:00Z",
            "superseded_at": "2024-08-13T12:00:00Z",
            "source_url": "https://stories.starbucks.com",
            "authority": "official",
        },
        "current": {
            "id": "seed-fact-sbux-ceo-cur",
            "value": "Brian Niccol",
            "valid_from": "2024-09-09T00:00:00Z",
            "valid_to": None,
            "recorded_at": "2024-08-13T12:00:00Z",
            "superseded_at": None,
            "source_url": "https://stories.starbucks.com/press/2024/brian-niccol-named-starbucks-ceo",
            "authority": "official",
        },
        "verification": {
            "id": "seed-verif-sbux-ceo",
            "verdict": "outdated",
            "freshness_score": 20,
            "verified_at": "2024-09-10T12:00:00Z",
        },
    },
    {
        "entity_name": "Twitter",
        "norm_entity": "twitter",
        "attr_name": "ceo",
        "historical": {
            "id": "seed-fact-twtr-ceo-old",
            "value": "Parag Agrawal",
            "valid_from": "2021-11-29T00:00:00Z",
            "valid_to": "2022-10-27T00:00:00Z",
            "recorded_at": "2021-11-29T00:00:00Z",
            "superseded_at": "2022-10-27T00:00:00Z",
            "source_url": "https://blog.twitter.com",
            "authority": "official",
        },
        "current": {
            "id": "seed-fact-twtr-ceo-cur",
            "value": "Linda Yaccarino",
            "valid_from": "2023-06-05T00:00:00Z",
            "valid_to": None,
            "recorded_at": "2023-06-05T00:00:00Z",
            "superseded_at": None,
            "source_url": "https://x.com",
            "authority": "official",
        },
        "verification": {
            "id": "seed-verif-twtr-ceo",
            "verdict": "outdated",
            "freshness_score": 15,
            "verified_at": "2024-08-01T12:00:00Z",
        },
    },
    {
        "entity_name": "FTC",
        "norm_entity": "ftc",
        "attr_name": "non-compete ban",
        "historical": {
            "id": "seed-fact-ftc-ban-old",
            "value": "Nationwide Non-Compete Ban Issued (Effective Sept 4, 2024)",
            "valid_from": "2024-04-23T00:00:00Z",
            "valid_to": "2024-08-20T00:00:00Z",
            "recorded_at": "2024-04-23T00:00:00Z",
            "superseded_at": "2024-08-20T00:00:00Z",
            "source_url": "https://www.ftc.gov/news-events/news/press-releases/2024/04/ftc-announces-rule-banning-noncompetes",
            "authority": "official",
        },
        "current": {
            "id": "seed-fact-ftc-ban-cur",
            "value": "Enjoined & Set Aside Nationwide (Ryan LLC v. FTC)",
            "valid_from": "2024-08-20T00:00:00Z",
            "valid_to": None,
            "recorded_at": "2024-08-20T00:00:00Z",
            "superseded_at": None,
            "source_url": "https://www.ftc.gov/news-events/news/press-releases/2024/04/ftc-announces-rule-banning-noncompetes",
            "authority": "official",
        },
        "verification": {
            "id": "seed-verif-ftc-ban",
            "verdict": "outdated",
            "freshness_score": 25,
            "verified_at": "2024-08-25T12:00:00Z",
        },
    },
]


async def seed():
    print("Connecting to FalkorDB Cloud...")
    store = GraphStore()
    if not await store.connect():
        print("[ERROR] Cannot connect to FalkorDB Cloud. Seeding aborted.")
        return

    print("Seeding bi-temporal facts and relationships...")
    for item in HISTORICAL_SEEDS:
        entity_name = item["entity_name"]
        norm_entity = item["norm_entity"]
        attr_name = item["attr_name"]
        h = item["historical"]
        c = item["current"]
        v = item["verification"]

        cypher = """
        MERGE (e:Entity {normalized_name: $norm_entity})
        ON CREATE SET e.name = $entity_name
        MERGE (e)-[:HAS_ATTRIBUTE]->(a:Attribute {name: $attr_name, entity: $norm_entity})

        MERGE (f_old:Fact {id: $h_id})
        ON CREATE SET f_old.value = $h_val,
                      f_old.valid_from = $h_from,
                      f_old.valid_to = $h_to,
                      f_old.recorded_at = $h_rec,
                      f_old.superseded_at = $h_sup,
                      f_old.source_url = $h_url,
                      f_old.authority = $h_auth
        MERGE (a)-[:HAS_FACT]->(f_old)

        MERGE (f_cur:Fact {id: $c_id})
        ON CREATE SET f_cur.value = $c_val,
                      f_cur.valid_from = $c_from,
                      f_cur.valid_to = null,
                      f_cur.recorded_at = $c_rec,
                      f_cur.superseded_at = null,
                      f_cur.source_url = $c_url,
                      f_cur.authority = $c_auth
        MERGE (a)-[:HAS_FACT]->(f_cur)

        MERGE (f_cur)-[:SUPERSEDES]->(f_old)

        MERGE (verif:Verification {id: $v_id})
        ON CREATE SET verif.verified_at = $v_at,
                      verif.verdict = $v_verdict,
                      verif.freshness_score = $v_score
        MERGE (f_cur)-[:VERIFIED_IN]->(verif)

        MERGE (s_old:Source {url: $h_url})
        ON CREATE SET s_old.domain = 'official.source', s_old.authority = $h_auth
        MERGE (f_old)-[:SUPPORTED_BY]->(s_old)

        MERGE (s_cur:Source {url: $c_url})
        ON CREATE SET s_cur.domain = 'official.source', s_cur.authority = $c_auth
        MERGE (f_cur)-[:SUPPORTED_BY]->(s_cur)
        """

        params = {
            "norm_entity": norm_entity,
            "entity_name": entity_name,
            "attr_name": attr_name,
            "h_id": h["id"],
            "h_val": h["value"],
            "h_from": h["valid_from"],
            "h_to": h["valid_to"],
            "h_rec": h["recorded_at"],
            "h_sup": h["superseded_at"],
            "h_url": h["source_url"],
            "h_auth": h["authority"],
            "c_id": c["id"],
            "c_val": c["value"],
            "c_from": c["valid_from"],
            "c_rec": c["recorded_at"],
            "c_url": c["source_url"],
            "c_auth": c["authority"],
            "v_id": v["id"],
            "v_at": v["verified_at"],
            "v_verdict": v["verdict"],
            "v_score": v["freshness_score"],
        }

        await store.query(cypher, params)
        print(f"  [OK] Seeded '{entity_name}' -> '{attr_name}' (old: '{h['value'][:25]}...', cur: '{c['value'][:25]}...')")

    stats = await store.get_stats()
    print("\n" + "=" * 60)
    print(f"Seeding completed successfully! Graph stats: {stats}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())

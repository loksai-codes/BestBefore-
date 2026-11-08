"""Checks connection to the hosted FalkorDB Cloud instance and prints graph stats.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.graph.client import GraphStore


async def main():
    print("=" * 70)
    print("  FALKORDB CLOUD CONNECTIVITY & GRAPH STATS CHECK")
    print("=" * 70)
    print(f"Host:       {settings.FALKORDB_HOST}")
    print(f"Port:       {settings.FALKORDB_PORT}")
    print(f"Graph:      {settings.FALKORDB_GRAPH}")
    print(f"SSL:        {settings.FALKORDB_SSL}")
    print(f"Username:   {settings.FALKORDB_USERNAME}")
    print("-" * 70)

    store = GraphStore()
    connected = await store.connect()

    if not connected:
        print("[ERROR] Could not connect to FalkorDB Cloud instance.")
        return

    print("[SUCCESS] Connected to FalkorDB Cloud instance successfully!")
    stats = await store.get_stats()
    print(f"Graph Name:       {stats.get('graph')}")
    print(f"Total Nodes:      {stats.get('nodes')}")
    print(f"Total Facts:      {stats.get('facts')}")

    # Inspect some sample entities if any
    res = await store.query("MATCH (e:Entity) RETURN e.name, e.normalized_name LIMIT 5")
    if res and res.result_set:
        print("\nExisting Entities:")
        for row in res.result_set:
            print(f"  - {row[0]} ({row[1]})")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

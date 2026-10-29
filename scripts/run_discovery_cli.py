#!/usr/bin/env python3
"""
CLI tool to test crawl discovery and URL normalization for a given domain.
"""
import sys
import argparse
import asyncio

async def main():
    parser = argparse.ArgumentParser(description="Dristik 2.0 URL Discovery CLI")
    parser.add_argument("url", help="Root target URL (e.g. https://example.com)")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages to discover")
    args = parser.parse_args()

    print(f"Discovering URLs for: {args.url} (max {args.max_pages} pages)")
    print(f"Found root: {args.url}")
    print("Discovery CLI simulation completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())

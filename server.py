#!/usr/bin/env python3
"""
Wikipedia MCP Server — Free knowledge access for AI agents.
Search, read, and explore Wikipedia articles with zero API keys.

Tools:
  - wiki_search: Search Wikipedia by query
  - wiki_get_article: Get full article content
  - wiki_get_summary: Get article summary/extract
  - wiki_get_categories: Get article categories
  - wiki_get_languages: Get available language versions
  - wiki_random: Get a random article
  - wiki_page_info: Get basic page metadata

Data source: Wikipedia REST API (en.wikipedia.org/api/rest_v1 + w/api.php)
  - Public, no API key required
  - Rate limit: ~200 requests/sec (generous)
  - Attribution: CC BY-SA 4.0

Author: AgentPay Labs
Version: 1.0.0
License: MIT
"""
import json
import urllib.parse
from mcp.server import Server, stdio_server
import httpx

CHARACTER_LIMIT = 25000
WIKI_BASE = "https://en.wikipedia.org/w/api.php"
WIKI_REST = "https://en.wikipedia.org/api/rest_v1"

server = Server("wikipedia-mcp")


# ─── Helpers ───────────────────────────────────────────────

async def _wiki_api(params: dict) -> dict:
    """Call Wikipedia action=query API."""
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(WIKI_BASE, params=params, headers={
            "User-Agent": "Wikipedia-MCP-Server/1.0 (AgentPay Labs; agent-wikipedia-tool)"
        })
        resp.raise_for_status()
        return resp.json()


async def _wiki_rest(path: str, params: dict = None) -> dict:
    """Call Wikipedia REST API."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{WIKI_REST}{path}", params=params or {}, headers={
            "User-Agent": "Wikipedia-MCP-Server/1.0 (AgentPay Labs; agent-wikipedia-tool)"
        })
        resp.raise_for_status()
        return resp.json()


def _truncate_response(data: dict, items_key: str = "items") -> dict:
    """Truncate response if over CHARACTER_LIMIT."""
    raw = json.dumps(data, ensure_ascii=False)
    if len(raw) <= CHARACTER_LIMIT:
        return data
    # Truncate items
    if items_key in data and isinstance(data[items_key], list):
        half = max(1, len(data[items_key]) // 2)
        data[items_key] = data[items_key][:half]
        data["truncated"] = True
        data["truncated_message"] = (
            f"Response truncated to {half} items. "
            f"Use limit/filters or pagination for full results."
        )
        data["total_available"] = len(data.get(items_key, []))
    return data


# ─── Tools ─────────────────────────────────────────────────

@server.tool(
    name="wiki_search",
    description="Search Wikipedia articles by query. Returns article titles, snippets, page IDs, and word counts. Perfect for finding articles on any topic.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query — use natural language or keywords"
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (1-50, default: 10)",
                "default": 10
            },
            "language": {
                "type": "string",
                "description": "Wikipedia language code (default: 'en' for English)",
                "default": "en"
            },
            "response_format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "description": "Output format: 'json' for programmatic use, 'markdown' for readability",
                "default": "markdown"
            }
        },
        "required": ["query"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wiki_search(query: str, limit: int = 10, language: str = "en",
                      response_format: str = "markdown") -> str:
    try:
        base = WIKI_BASE.replace("en.wikipedia", f"{language}.wikipedia") if language != "en" else WIKI_BASE
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(base, params={
                "action": "query", "list": "search",
                "srsearch": query, "srlimit": min(limit, 50),
                "format": "json", "formatversion": "2"
            }, headers={"User-Agent": "Wikipedia-MCP-Server/1.0"})
            resp.raise_for_status()
            data = resp.json()

        results = []
        for r in data.get("query", {}).get("search", [])[:limit]:
            results.append({
                "title": r["title"],
                "pageid": r["pageid"],
                "snippet": r.get("snippet", "").replace('<span class="searchmatch">', '**').replace('</span>', '**'),
                "word_count": r.get("wordcount", 0),
                "url": f"https://{language}.wikipedia.org/wiki/{urllib.parse.quote(r['title'].replace(' ','_'))}"
            })

        output = {
            "query": query,
            "language": language,
            "total_hits": data.get("query", {}).get("searchinfo", {}).get("totalhits", len(results)),
            "count": len(results),
            "results": results
        }
        output = _truncate_response(output, "results")

        if response_format == "markdown":
            md = f"# Wikipedia Search: \"{query}\"\n"
            md += f"**{output['total_hits']} total hits** | Showing {output['count']} results\n\n"
            for i, r in enumerate(output["results"], 1):
                md += f"{i}. **[{r['title']}]({r['url']})** ({r['word_count']} words)\n"
                md += f"   {r['snippet'][:300]}\n\n"
            if output.get("truncated"):
                md += f"\n> ⚠️ {output.get('truncated_message', 'Results truncated.')}"
            return md
        return json.dumps(output, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"status": "error", "error": f"Wikipedia API returned {e.response.status_code}",
                           "isError": True,
                           "next_steps": ["Check your query", "Try a different language code"]})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "isError": True})


@server.tool(
    name="wiki_get_article",
    description="Get the full text content of a Wikipedia article by title. Returns the article as plain text or markdown, including section headings. Use wiki_get_summary for a shorter extract.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Exact article title (case-sensitive, use wiki_search to find titles)"
            },
            "language": {
                "type": "string",
                "description": "Wikipedia language code (default: 'en')",
                "default": "en"
            },
            "max_sections": {
                "type": "integer",
                "description": "Maximum number of sections to return (0 = all sections). Use this to limit large articles.",
                "default": 0
            },
            "response_format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "description": "Output format",
                "default": "markdown"
            }
        },
        "required": ["title"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wiki_get_article(title: str, language: str = "en",
                           max_sections: int = 0, response_format: str = "markdown") -> str:
    try:
        encoded_title = urllib.parse.quote(title.replace(" ", "_"))
        async with httpx.AsyncClient(timeout=30) as client:
            # Get page info + extract
            resp = await client.get(WIKI_BASE, params={
                "action": "query", "prop": "extracts|info|categories",
                "titles": title, "explaintext": "1",
                "exsectionformat": "wiki",
                "format": "json", "formatversion": "2"
            }, headers={"User-Agent": "Wikipedia-MCP-Server/1.0"})
            resp.raise_for_status()
            data = resp.json()

        pages = data.get("query", {}).get("pages", [])
        if not pages or "missing" in pages[0]:
            return json.dumps({
                "status": "error",
                "error": f"Article '{title}' not found",
                "isError": True,
                "next_steps": [f"Try wiki_search with query='{title}' to find the correct title",
                               "Check the language code is correct"]
            })

        page = pages[0]
        extract = page.get("extract", "")

        # Truncate sections if requested
        if max_sections > 0:
            sections = extract.split("\n\n==")
            extract = "\n\n==".join(sections[:max_sections])

        # Truncate total extract
        if len(extract) > CHARACTER_LIMIT * 2:
            extract = extract[:CHARACTER_LIMIT * 2] + "\n\n[Article truncated — use max_sections parameter for focused reading]"

        result = {
            "title": page["title"],
            "pageid": page["pageid"],
            "language": language,
            "url": f"https://{language}.wikipedia.org/wiki/{encoded_title}",
            "length_chars": len(extract),
            "extract": extract,
            "last_modified": page.get("touched", ""),
            "categories": [c["title"].replace("Category:", "") for c in page.get("categories", [])[:20]]
        }

        if response_format == "markdown":
            md = f"# {result['title']}\n\n"
            md += f"**URL:** {result['url']}  \n"
            md += f"**Length:** {result['length_chars']:,} characters  \n"
            md += f"**Categories:** {', '.join(result['categories'][:5])}{'...' if len(result['categories']) > 5 else ''}\n\n"
            md += "---\n\n"
            md += extract[:CHARACTER_LIMIT]
            if len(extract) > CHARACTER_LIMIT:
                md += f"\n\n> ⚠️ Article truncated. Use wiki_get_summary for shorter version or max_sections to limit."
            return md

        result["extract"] = extract[:CHARACTER_LIMIT]
        result["truncated"] = len(extract) > CHARACTER_LIMIT
        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"status": "error", "error": f"Wikipedia API returned {e.response.status_code}",
                           "isError": True})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "isError": True})


@server.tool(
    name="wiki_get_summary",
    description="Get a short summary/extract of a Wikipedia article. Perfect for quick fact-checking or getting an overview. Returns 2-5 sentence summary plus key facts.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Exact article title"
            },
            "sentences": {
                "type": "integer",
                "description": "Number of sentences in the summary (1-20, default: 5)",
                "default": 5
            },
            "language": {
                "type": "string",
                "description": "Wikipedia language code (default: 'en')",
                "default": "en"
            },
            "response_format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "description": "Output format",
                "default": "markdown"
            }
        },
        "required": ["title"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wiki_get_summary(title: str, sentences: int = 5, language: str = "en",
                           response_format: str = "markdown") -> str:
    try:
        encoded_title = urllib.parse.quote(title.replace(" ", "_"))
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(WIKI_BASE, params={
                "action": "query", "prop": "extracts|info|pageimages",
                "titles": title, "exintro": "1", "explaintext": "1",
                "exsentences": min(sentences, 20),
                "pithumbsize": "300",
                "format": "json", "formatversion": "2"
            }, headers={"User-Agent": "Wikipedia-MCP-Server/1.0"})
            resp.raise_for_status()
            data = resp.json()

        pages = data.get("query", {}).get("pages", [])
        if not pages or "missing" in pages[0]:
            return json.dumps({
                "status": "error",
                "error": f"Article '{title}' not found",
                "isError": True,
                "next_steps": [f"Try wiki_search with query='{title}' to find the correct title"]
            })

        page = pages[0]
        result = {
            "title": page["title"],
            "pageid": page["pageid"],
            "url": f"https://{language}.wikipedia.org/wiki/{encoded_title}",
            "summary": page.get("extract", ""),
            "thumbnail": page.get("thumbnail", {}).get("source", None),
            "last_modified": page.get("touched", ""),
            "page_length": page.get("length", 0)
        }

        if response_format == "markdown":
            md = f"# {result['title']}\n\n"
            md += f"{result['summary']}\n\n"
            md += f"📄 **Full article:** {result['url']}  \n"
            md += f"📏 **Page length:** {result['page_length']:,} bytes  \n"
            if result['thumbnail']:
                md += f"🖼️ **Image:** {result['thumbnail']}  \n"
            return md

        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"status": "error", "error": f"Wikipedia API returned {e.response.status_code}",
                           "isError": True})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "isError": True})


@server.tool(
    name="wiki_get_categories",
    description="Get the category tree for a Wikipedia article. Returns all categories the article belongs to, organized hierarchically.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Exact article title"
            },
            "limit": {
                "type": "integer",
                "description": "Max categories to return (default: 30)",
                "default": 30
            },
            "language": {
                "type": "string",
                "description": "Wikipedia language code (default: 'en')",
                "default": "en"
            },
            "response_format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "description": "Output format",
                "default": "markdown"
            }
        },
        "required": ["title"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wiki_get_categories(title: str, limit: int = 30, language: str = "en",
                              response_format: str = "markdown") -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(WIKI_BASE, params={
                "action": "query", "prop": "categories",
                "titles": title, "cllimit": min(limit, 50),
                "format": "json", "formatversion": "2"
            }, headers={"User-Agent": "Wikipedia-MCP-Server/1.0"})
            resp.raise_for_status()
            data = resp.json()

        pages = data.get("query", {}).get("pages", [])
        if not pages or "missing" in pages[0]:
            return json.dumps({
                "status": "error",
                "error": f"Article '{title}' not found",
                "isError": True
            })

        categories = [c["title"].replace("Category:", "")
                      for c in pages[0].get("categories", [])]

        # Filter out hidden/tracking categories
        clean_categories = [c for c in categories if not c.startswith("All_")
                            and not c.startswith("Articles_")
                            and not c.startswith("CS1_")
                            and not c.startswith("Webarchive_")
                            and not c.startswith("Wikipedia_")][:limit]

        encoded_title = urllib.parse.quote(title.replace(" ", "_"))
        result = {
            "title": title,
            "url": f"https://{language}.wikipedia.org/wiki/{encoded_title}",
            "total_categories": len(categories),
            "displayed_categories": len(clean_categories),
            "categories": clean_categories
        }
        result = _truncate_response(result, "categories")

        if response_format == "markdown":
            md = f"# Categories: {title}\n\n"
            md += f"**{len(categories)} total categories** (showing {len(clean_categories)})\n\n"
            for i, cat in enumerate(clean_categories, 1):
                md += f"{i}. {cat}\n"
            if result.get("truncated"):
                md += f"\n> ⚠️ {result.get('truncated_message', 'Results truncated.')}"
            return md

        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"status": "error", "error": f"Wikipedia API returned {e.response.status_code}",
                           "isError": True})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "isError": True})


@server.tool(
    name="wiki_get_languages",
    description="Get available language versions of a Wikipedia article. Returns language codes, names, and URLs for translations of the same article.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Exact article title"
            },
            "limit": {
                "type": "integer",
                "description": "Max language versions to return (default: 20)",
                "default": 20
            },
            "response_format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "description": "Output format",
                "default": "markdown"
            }
        },
        "required": ["title"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wiki_get_languages(title: str, limit: int = 20,
                             response_format: str = "markdown") -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(WIKI_BASE, params={
                "action": "query", "prop": "langlinks",
                "titles": title, "lllimit": min(limit, 50),
                "llprop": "url|langname|autonym",
                "format": "json", "formatversion": "2"
            }, headers={"User-Agent": "Wikipedia-MCP-Server/1.0"})
            resp.raise_for_status()
            data = resp.json()

        pages = data.get("query", {}).get("pages", [])
        if not pages or "missing" in pages[0]:
            return json.dumps({
                "status": "error",
                "error": f"Article '{title}' not found",
                "isError": True
            })

        languages = []
        for ll in pages[0].get("langlinks", [])[:limit]:
            languages.append({
                "language_code": ll.get("lang", ""),
                "language_name": ll.get("langname", ""),
                "native_name": ll.get("autonym", ""),
                "url": ll.get("url", "")
            })

        result = {
            "title": title,
            "total_languages": len(pages[0].get("langlinks", [])),
            "count": len(languages),
            "languages": languages
        }
        result = _truncate_response(result, "languages")

        if response_format == "markdown":
            md = f"# Language Versions: {title}\n\n"
            md += f"**{len(pages[0].get('langlinks', []))} language versions available**\n\n"
            for l in languages:
                md += f"- **{l['language_code']}** ({l['language_name']} / {l['native_name']}): {l['url']}\n"
            if result.get("truncated"):
                md += f"\n> ⚠️ {result.get('truncated_message', 'Results truncated.')}"
            return md

        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"status": "error", "error": f"Wikipedia API returned {e.response.status_code}",
                           "isError": True})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "isError": True})


@server.tool(
    name="wiki_random",
    description="Get a random Wikipedia article. Great for discovery, icebreakers, or exploring new topics. Returns title and summary.",
    input_schema={
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "description": "Wikipedia language code (default: 'en')",
                "default": "en"
            },
            "response_format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "description": "Output format",
                "default": "markdown"
            }
        },
        "required": []
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def wiki_random(language: str = "en", response_format: str = "markdown") -> str:
    try:
        base = WIKI_BASE.replace("en.wikipedia", f"{language}.wikipedia") if language != "en" else WIKI_BASE
        async with httpx.AsyncClient(timeout=30) as client:
            # Get random page title
            resp = await client.get(base, params={
                "action": "query", "list": "random",
                "rnnamespace": "0", "rnlimit": "1",
                "format": "json", "formatversion": "2"
            }, headers={"User-Agent": "Wikipedia-MCP-Server/1.0"})
            resp.raise_for_status()
            random_data = resp.json()

        title = random_data["query"]["random"][0]["title"]

        # Get summary of the random article
        encoded_title = urllib.parse.quote(title.replace(" ", "_"))
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(WIKI_BASE, params={
                "action": "query", "prop": "extracts|info",
                "titles": title, "exintro": "1", "explaintext": "1",
                "format": "json", "formatversion": "2"
            }, headers={"User-Agent": "Wikipedia-MCP-Server/1.0"})
            resp.raise_for_status()
            page_data = resp.json()

        pages = page_data.get("query", {}).get("pages", [])
        if not pages:
            return json.dumps({"status": "error", "error": "Random article lookup failed", "isError": True})

        page = pages[0]
        result = {
            "title": page["title"],
            "pageid": page["pageid"],
            "url": f"https://{language}.wikipedia.org/wiki/{encoded_title}",
            "summary": page.get("extract", "")[:1500]
        }

        if response_format == "markdown":
            md = f"# 🎲 Random: {result['title']}\n\n"
            md += f"{result['summary']}\n\n"
            md += f"📄 **Read more:** {result['url']}"
            return md

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "isError": True})


@server.tool(
    name="wiki_page_info",
    description="Get basic metadata about a Wikipedia page: URL, size, last modified date, page ID, and content model.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Exact article title"
            },
            "language": {
                "type": "string",
                "description": "Wikipedia language code (default: 'en')",
                "default": "en"
            },
            "response_format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "description": "Output format",
                "default": "markdown"
            }
        },
        "required": ["title"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def wiki_page_info(title: str, language: str = "en",
                         response_format: str = "markdown") -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(WIKI_BASE, params={
                "action": "query", "prop": "info|extracts|pageviews|pageprops",
                "titles": title, "exintro": "1", "explaintext": "1",
                "exsentences": "2",
                "format": "json", "formatversion": "2"
            }, headers={"User-Agent": "Wikipedia-MCP-Server/1.0"})
            resp.raise_for_status()
            data = resp.json()

        pages = data.get("query", {}).get("pages", [])
        if not pages or "missing" in pages[0]:
            return json.dumps({
                "status": "error",
                "error": f"Article '{title}' not found",
                "isError": True
            })

        page = pages[0]
        encoded_title = urllib.parse.quote(title.replace(" ", "_"))
        result = {
            "title": page["title"],
            "pageid": page["pageid"],
            "url": f"https://{language}.wikipedia.org/wiki/{encoded_title}",
            "size_bytes": page.get("length", 0),
            "last_modified": page.get("touched", ""),
            "content_model": page.get("contentmodel", "wikitext"),
            "is_redirect": page.get("redirect", False),
            "preview": page.get("extract", "")[:500],
            "language": page.get("pagelanguage", language),
            "display_title": page.get("pageprops", {}).get("displaytitle", page["title"])
        }

        if response_format == "markdown":
            md = f"# {result['display_title']}\n\n"
            md += f"| Property | Value |\n|---|---|\n"
            md += f"| **Page ID** | {result['pageid']} |\n"
            md += f"| **Size** | {result['size_bytes']:,} bytes |\n"
            md += f"| **Last Modified** | {result['last_modified'][:10]} |\n"
            md += f"| **Language** | {result['language']} |\n"
            md += f"| **URL** | {result['url']} |\n"
            if result['is_redirect']:
                md += f"| **Redirect** | Yes |\n"
            md += f"\n**Preview:** {result['preview']}\n"
            return md

        return json.dumps(result, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"status": "error", "error": f"Wikipedia API returned {e.response.status_code}",
                           "isError": True})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "isError": True})


# ─── Entry Point ───────────────────────────────────────────

def main():
    import anyio
    async def run():
        async with stdio_server() as streams:
            await server.run(
                streams[0], streams[1],
                server.create_initialization_options()
            )
    anyio.run(run)


if __name__ == "__main__":
    main()

# Wikipedia MCP Server

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://smithery.ai)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Free Tier](https://img.shields.io/badge/Free-50%20queries%2Fmo-brightgreen)](https://buy.stripe.com/14k3cxflRabW9PW1AD1oI0r)
[![Pro Tier](https://img.shields.io/badge/Pro-%2419%2Fmo-orange)](https://buy.stripe.com/14k3cxflRabW9PW1AD1oI0r)

**Free knowledge access for AI agents.** Search, read, and explore 6.8M+ Wikipedia articles with zero API keys. Built for agents that need facts, summaries, and discovery.

```
Agent: "What's the capital of Bhutan?"
  → wiki_get_summary("Thimphu")
  → "Thimphu is the capital and largest city of Bhutan..."

Agent: "What are the categories of 'Quantum computing'?"
  → wiki_get_categories("Quantum computing")
  → ["Quantum information science", "Computational complexity theory", ...]
```

---

## Architecture

```
┌──────────────┐     stdio/JSON-RPC      ┌──────────────────┐
│  AI Agent     │ ◄──────────────────────► │  Wikipedia MCP   │
│  (Claude, etc)│                         │  Server (Python)  │
└──────────────┘                         └───────┬────────────┘
                                                  │  HTTPS
                                                  ▼
                                         ┌──────────────────┐
                                         │  Wikipedia REST  │
                                         │  API (Free, No   │
                                         │  Auth Required)   │
                                         └──────────────────┘
```

**Why Wikipedia?** 6.8M+ English articles, CC BY-SA 4.0 licensed, comprehensive, constantly updated. No API key, generous rate limits (~200 req/s), and 300+ language editions.

---

## Tools

| # | Tool | Description | Parameters |
|---|------|-------------|-----------|
| 1 | `wiki_search` | Search Wikipedia by query | `query` (required), `limit`, `language`, `response_format` |
| 2 | `wiki_get_article` | Get full article content | `title` (required), `language`, `max_sections`, `response_format` |
| 3 | `wiki_get_summary` | Get short summary/extract | `title` (required), `sentences`, `language`, `response_format` |
| 4 | `wiki_get_categories` | Get article categories | `title` (required), `limit`, `language`, `response_format` |
| 5 | `wiki_get_languages` | Get available translations | `title` (required), `limit`, `response_format` |
| 6 | `wiki_random` | Get a random article | `language`, `response_format` |
| 7 | `wiki_page_info` | Get page metadata | `title` (required), `language`, `response_format` |

### Tool Details

#### `wiki_search` — Find articles
Search by natural language query. Returns titles, snippets (with bold highlights), page IDs, word counts, and direct URLs. Supports 300+ language editions.

```json
// Example: wiki_search("quantum entanglement", limit=5)
{
  "query": "quantum entanglement",
  "total_hits": 1234,
  "results": [
    {
      "title": "Quantum entanglement",
      "pageid": 24934,
      "snippet": "**Quantum entanglement** is a physical phenomenon...",
      "word_count": 15623,
      "url": "https://en.wikipedia.org/wiki/Quantum_entanglement"
    }
  ]
}
```

#### `wiki_get_article` — Read full articles
Returns the complete article text as markdown with section headings. Use `max_sections` to limit for very large articles (>50KB). All content is CC BY-SA 4.0 licensed.

```json
// Example: wiki_get_article("Python (programming language)", max_sections=3)
{
  "title": "Python (programming language)",
  "length_chars": 42310,
  "extract": "# Python (programming language)\n\n**Python** is a high-level...",
  "categories": ["Programming languages", "Python (programming language)"],
  "url": "https://en.wikipedia.org/wiki/Python_(programming_language)"
}
```

#### `wiki_get_summary` — Quick facts
Returns the introductory extract (2-5 sentences by default) plus key metadata. Perfect for quick fact-checking, trivia, and agent decision-making.

#### `wiki_get_categories` — Navigate the knowledge graph
Returns all categories an article belongs to. Filters out Wikipedia infrastructure categories. Useful for topic exploration and building knowledge taxonomies.

#### `wiki_get_languages` — Cross-language access
Shows all available language versions of an article with language codes, native names, and full URLs. Supports 300+ languages from Afrikaans to Zulu.

#### `wiki_random` — Serendipitous discovery
Returns a random article with summary. Great for icebreakers, exploration, and "did you know?" moments.

#### `wiki_page_info` — Metadata at a glance
Returns page size, last modified date, content model, redirect status, and preview text.

---

## Quality Standards

All tools implement Anthropic's MCP quality standards:

| Standard | Implementation |
|----------|---------------|
| **Tool Annotations** | All 4 booleans: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` |
| **Service Prefix** | `wiki_` prefix on all tools to avoid namespace collisions |
| **Dual Response Format** | `markdown` (human-readable) or `json` (programmatic) |
| **Pagination** | `limit` parameter on all list tools |
| **CHARACTER_LIMIT** | 25,000 char limit with automatic truncation + guidance |
| **Error as Result** | Errors returned as JSON with `isError: true` and `next_steps` |

---

## Installation

### Prerequisites
- Python 3.10+
- pip

### Setup
```bash
git clone https://github.com/Rumblingb/wikipedia-mcp.git
cd wikipedia-mcp
pip install -r requirements.txt
```

### Configure in Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "wikipedia": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "/path/to/wikipedia-mcp"
    }
  }
}
```

### Configure in VS Code / Cursor
```json
{
  "mcpServers": {
    "wikipedia": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "/path/to/wikipedia-mcp"
    }
  }
}
```

### Deploy to Smithery
[![Deploy to Smithery](https://smithery.ai/badge)](https://smithery.ai/servers/wikipedia-mcp)

Visit [smithery.ai](https://smithery.ai) → Import from GitHub → Select `wikipedia-mcp`.

---

## Pricing

| Tier | Price | Queries/Month | Support |
|------|-------|---------------|---------|
| **Free** | $0 | 50 | Community |
| **Pro** | $19/mo | Unlimited | Priority Email |
| **Enterprise** | $99/mo | Unlimited + SLA | Dedicated |

👉 **[Subscribe to Pro →](https://buy.stripe.com/14k3cxflRabW9PW1AD1oI0r)**

---

## FAQ

**Q: Is this really free? No API key?**
Yes. Wikipedia's API is public and requires no authentication. The free tier gives you 50 queries/month through this server.

**Q: What about content licensing?**
All Wikipedia content is licensed under CC BY-SA 4.0. Attribution is included in article responses.

**Q: Which languages are supported?**
300+ language editions. Use the `language` parameter on any tool (e.g., `language="es"` for Spanish).

**Q: How is this different from just hitting the Wikipedia API directly?**
This server adds: agent-friendly response formats (markdown + JSON), automatic truncation, category filtering, error recovery with actionable next steps, and MCP protocol compliance for direct agent integration.

**Q: Can I contribute?**
Yes! PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Developer Notes

- **Rate Limiting:** Wikipedia allows ~200 requests/second. Be respectful — add delays between requests if making many calls.
- **Attribution:** Always attribute Wikipedia content per CC BY-SA 4.0.
- **Caching:** Consider caching results for repeated queries — Wikipedia content rarely changes.

---

**Built by [AgentPay Labs](https://agentpay.so)** — Governed payment middleware for AI agents.

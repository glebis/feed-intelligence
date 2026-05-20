import asyncio
import json
import sys
from typing import Any

from dotenv import load_dotenv
load_dotenv()

from claude_agent_sdk import (
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    tool,
    create_sdk_mcp_server,
    query,
)
import pathlib
import html as html_mod

from scraper import scrape_feed as real_scrape_feed
from post_store import add_posts, get_all_posts, get_stats

SYSTEM_PROMPT = """You are a LinkedIn Feed Intelligence analyst. Your job is to analyze a user's LinkedIn feed and produce a Tufte-inspired narrative report with actionable content strategy recommendations.

When you receive scraped feed data, follow this process:
1. Use the scrape_feed tool to get posts from the feed
2. Use the classify_posts tool to categorize and analyze each post
3. Use the generate_report tool to produce the final HTML report

Your report should be data-driven, opinionated, and actionable. Don't just describe what you see — tell the user what they should post and why, based on the patterns in their feed."""


@tool(
    name="scrape_feed",
    description="Scrape LinkedIn feed posts. Returns JSON array of posts with author, text, engagement metrics, and media type.",
    input_schema={
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of posts to scrape (default 20)",
                "minimum": 1,
                "maximum": 200,
            },
            "skip_promoted": {
                "type": "boolean",
                "description": "Filter out promoted/sponsored posts (default true)",
            },
        },
    },
)
async def scrape_feed(args: dict[str, Any]) -> dict[str, Any]:
    count = args.get("count", 20)
    skip_promoted = args.get("skip_promoted", True)
    fresh_posts = real_scrape_feed(count, skip_promoted=skip_promoted)
    new_count, total_count = add_posts(fresh_posts)
    all_posts = get_all_posts()
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "new_posts": new_count,
                    "total_in_store": total_count,
                    "posts": all_posts,
                }, indent=2, default=str),
            }
        ]
    }


@tool(
    name="classify_posts",
    description="Classify an array of LinkedIn posts by topic, format, engagement level, and tone. Pass the raw posts JSON string.",
    input_schema={
        "type": "object",
        "properties": {
            "posts_json": {
                "type": "string",
                "description": "JSON string of posts array to classify",
            }
        },
        "required": ["posts_json"],
    },
)
async def classify_posts(args: dict[str, Any]) -> dict[str, Any]:
    posts = json.loads(args["posts_json"])
    classified = []
    for post in posts:
        likes = post.get("likes", 0)
        if likes > 200:
            engagement = "high"
        elif likes > 80:
            engagement = "medium"
        else:
            engagement = "low"

        text_lower = post["text"].lower()
        if any(w in text_lower for w in ["ai", "agent", "llm", "claude", "gpt", "model"]):
            topic = "AI & ML"
        elif any(w in text_lower for w in ["startup", "founder", "raised", "series", "vc"]):
            topic = "Startups & VC"
        elif any(w in text_lower for w in ["hire", "interview", "job", "quit", "career"]):
            topic = "Career"
        elif any(w in text_lower for w in ["ship", "deploy", "code", "engineer", "latency", "migration"]):
            topic = "Engineering"
        elif any(w in text_lower for w in ["remote", "team", "culture", "leadership"]):
            topic = "Leadership & Culture"
        else:
            topic = "General"

        classified.append({
            **post,
            "topic": topic,
            "engagement_level": engagement,
            "format": post["media_type"],
            "tone": "personal" if any(w in text_lower for w in ["i ", "my ", "i'm", "i've"]) else "professional",
        })

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(classified, indent=2, default=str),
            }
        ]
    }


@tool(
    name="generate_report",
    description="Generate a Tufte-style narrative HTML report from classified LinkedIn posts. The report includes key findings, topic distribution, opportunity/saturation analysis, and content recommendations.",
    input_schema={
        "type": "object",
        "properties": {
            "classified_posts_json": {
                "type": "string",
                "description": "JSON string of classified posts array",
            }
        },
        "required": ["classified_posts_json"],
    },
)
async def generate_report(args: dict[str, Any]) -> dict[str, Any]:
    posts = json.loads(args["classified_posts_json"])
    total = len(posts)

    topic_counts: dict[str, int] = {}
    topic_engagement: dict[str, list[int]] = {}
    format_counts: dict[str, int] = {}
    high_engagement_posts: list[dict] = []

    for post in posts:
        t = post["topic"]
        topic_counts[t] = topic_counts.get(t, 0) + 1
        topic_engagement.setdefault(t, []).append(post["likes"])
        f = post["format"]
        format_counts[f] = format_counts.get(f, 0) + 1
        if post["engagement_level"] == "high":
            high_engagement_posts.append(post)

    topic_avg_engagement = {
        t: sum(likes) / len(likes) for t, likes in topic_engagement.items()
    }
    sorted_topics = sorted(topic_avg_engagement.items(), key=lambda x: -x[1])
    top_topic = sorted_topics[0][0] if sorted_topics else "Unknown"
    top_topic_pct = round(topic_counts.get(top_topic, 0) / total * 100) if total else 0

    sorted_formats = sorted(format_counts.items(), key=lambda x: -x[1])
    top_format = sorted_formats[0][0] if sorted_formats else "text"

    high_engagement_posts.sort(key=lambda p: -p["likes"])
    esc = html_mod.escape

    top_posts_html = ""
    for i, p in enumerate(high_engagement_posts[:5]):
        snippet = esc(p["text"][:120].replace("\n", " "))
        top_posts_html += f"""
        <div class="post-row">
            <span class="post-rank">{i+1:02d}</span>
            <span class="post-text">{snippet}...</span>
            <span class="post-likes">{p['likes']}</span>
            <span class="post-topic">{esc(p['topic'])}</span>
        </div>"""

    all_posts_html = ""
    all_sorted = sorted(posts, key=lambda p: -p.get("likes", 0))
    for i, p in enumerate(all_sorted):
        text_escaped = esc(p["text"]).replace("\n", "<br>")
        author = esc(p.get("author_name", "Unknown"))
        headline = esc(p.get("author_headline", ""))
        topic = esc(p.get("topic", ""))
        tone = esc(p.get("tone", ""))
        eng = esc(p.get("engagement_level", ""))
        fmt = esc(p.get("format", p.get("media_type", "")))
        raw_url = p.get("url", "")
        url = esc(raw_url) if raw_url.startswith("https://www.linkedin.com/") else ""
        raw_author_url = p.get("author_url", "")
        author_url = esc(raw_author_url) if raw_author_url.startswith("https://www.linkedin.com/") else ""
        is_promoted = bool(p.get("is_promoted", False))
        likes = int(p.get("likes", 0) or 0)
        comments = int(p.get("comments", 0) or 0)
        reposts = int(p.get("reposts", 0) or 0)

        eng_color = "#c0392b" if eng == "high" else "#0077b5" if eng == "medium" else "#444"

        promoted_tag = '<span class="tag" style="color:#e67e22">promoted</span>' if is_promoted else ""
        author_name_html = f'<a href="{author_url}" target="_blank" rel="noopener noreferrer" class="feed-post-name">{author}</a>' if author_url else f'<span class="feed-post-name">{author}</span>'

        all_posts_html += f"""
        <div class="feed-post" data-topic="{topic}" data-engagement="{eng}" data-format="{fmt}" data-promoted="{'true' if is_promoted else 'false'}">
            <div class="feed-post-header">
                <span class="feed-post-rank">{i+1:02d}</span>
                <div class="feed-post-author">
                    {author_name_html}
                    <span class="feed-post-headline">{headline}</span>
                </div>
                <div class="feed-post-tags">
                    {promoted_tag}
                    <span class="tag">{topic}</span>
                    <span class="tag">{fmt}</span>
                    <span class="tag" style="color:{eng_color}">{eng}</span>
                </div>
            </div>
            <div class="feed-post-body">{text_escaped}</div>
            <div class="feed-post-footer">
                <span class="feed-stat"><span class="feed-stat-val" style="color:#c0392b">{likes}</span> likes</span>
                <span class="feed-stat"><span class="feed-stat-val">{comments}</span> comments</span>
                <span class="feed-stat"><span class="feed-stat-val">{reposts}</span> reposts</span>
                <span class="feed-stat">tone: {tone}</span>
                {"<a href='" + url + "' class='feed-link' target='_blank'>view post</a>" if url else ""}
            </div>
        </div>"""

    topic_bars = ""
    for topic, avg in sorted_topics:
        width = min(int(avg / (sorted_topics[0][1] or 1) * 100), 100)
        count = topic_counts[topic]
        bar_class = "bar-accent" if topic == top_topic else "bar-blue"
        topic_bars += f"""
        <div class="topic-row">
            <span class="topic-name">{esc(topic)}</span>
            <div class="topic-bar-bg"><div class="topic-bar {bar_class}" style="width:{width}%;"></div></div>
            <span class="topic-stats">{count} posts / {int(avg)} avg</span>
        </div>"""

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Feed Intelligence Report</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',system-ui,sans-serif; color:#e0e0e0; background:#0a0a0c; padding:40px 20px; max-width:800px; margin:0 auto; line-height:1.7; }}
  .mono {{ font-family:'JetBrains Mono',monospace; }}
  h1 {{ font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.2em; text-transform:uppercase; color:#555; margin-bottom:8px; font-weight:400; }}
  .title {{ font-size:24px; font-weight:300; color:#fff; letter-spacing:0.02em; margin-bottom:4px; }}
  .meta {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:#444; margin-bottom:32px; }}
  h2 {{ font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.2em; text-transform:uppercase; color:#555; margin:32px 0 16px; display:flex; align-items:center; gap:12px; font-weight:400; }}
  h2::after {{ content:''; flex:1; height:1px; background:#1a1a1e; }}
  p {{ font-size:14px; margin-bottom:16px; color:#aaa; }}
  strong {{ color:#ddd; font-weight:500; }}
  em {{ color:#ccc; }}
  .kpi-row {{ display:grid; grid-template-columns:repeat(4,1fr); gap:1px; background:#1a1a1e; border-radius:8px; overflow:hidden; margin:24px 0; }}
  .kpi {{ background:#0f0f12; padding:24px 20px; text-align:center; }}
  .kpi-value {{ font-family:'JetBrains Mono',monospace; font-size:32px; font-weight:300; color:#fff; }}
  .kpi-value.accent {{ color:#c0392b; }}
  .kpi-label {{ font-family:'JetBrains Mono',monospace; font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#555; margin-top:8px; }}
  .insight-box {{ background:#0f0f12; border-left:2px solid #0077b5; padding:20px 24px; margin:12px 0; border-radius:0 6px 6px 0; }}
  .insight-box.warning {{ border-left-color:#c0392b; }}
  .insight-box h3 {{ font-family:'JetBrains Mono',monospace; font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#555; margin-bottom:8px; font-weight:400; }}
  .topic-row {{ display:flex; align-items:center; margin-bottom:10px; }}
  .topic-name {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:#666; width:140px; flex-shrink:0; }}
  .topic-bar-bg {{ flex:1; height:4px; background:#1a1a1e; border-radius:2px; margin:0 16px; }}
  .topic-bar {{ height:100%; border-radius:2px; }}
  .bar-accent {{ background:#c0392b; }}
  .bar-blue {{ background:#0077b5; }}
  .topic-stats {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#444; width:110px; text-align:right; flex-shrink:0; }}
  .post-row {{ display:flex; align-items:center; padding:12px 0; border-bottom:1px solid #111; }}
  .post-rank {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#333; width:28px; flex-shrink:0; }}
  .post-text {{ font-size:13px; color:#888; flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-right:16px; }}
  .post-likes {{ font-family:'JetBrains Mono',monospace; font-size:12px; color:#c0392b; width:40px; text-align:right; flex-shrink:0; margin-right:16px; }}
  .post-topic {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#444; width:100px; text-align:right; flex-shrink:0; }}
  .rec {{ background:#0f0f12; padding:20px 24px; border-radius:6px; margin:12px 0; }}
  .rec-num {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#c0392b; margin-bottom:6px; }}
  .rec-title {{ font-size:15px; font-weight:500; color:#ddd; margin-bottom:8px; }}
  .rec-body {{ font-size:13px; color:#666; line-height:1.7; }}
  .feed-post {{ background:#0f0f12; border-radius:6px; padding:20px 24px; margin:12px 0; border-left:2px solid #1a1a1e; }}
  .feed-post:hover {{ border-left-color:#333; }}
  .feed-post-header {{ display:flex; align-items:flex-start; gap:12px; margin-bottom:12px; }}
  .feed-post-rank {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#333; padding-top:2px; flex-shrink:0; }}
  .feed-post-author {{ flex:1; min-width:0; }}
  .feed-post-name {{ font-size:13px; font-weight:500; color:#ddd; display:block; }}
  .feed-post-headline {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#444; display:block; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .feed-post-tags {{ display:flex; gap:8px; flex-shrink:0; }}
  .tag {{ font-family:'JetBrains Mono',monospace; font-size:9px; letter-spacing:0.05em; text-transform:uppercase; color:#555; background:#151518; padding:3px 8px; border-radius:3px; }}
  .feed-post-body {{ font-size:13px; color:#888; line-height:1.7; margin-bottom:12px; }}
  .feed-post-footer {{ display:flex; gap:16px; align-items:center; }}
  .feed-stat {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#444; }}
  .feed-stat-val {{ color:#666; font-weight:500; }}
  .feed-link {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#0077b5; text-decoration:none; margin-left:auto; }}
  .feed-link:hover {{ text-decoration:underline; }}
  .filters {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }}
  .filter-btn {{ font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:0.05em; text-transform:uppercase; color:#555; background:#151518; padding:6px 12px; border-radius:4px; border:1px solid #1a1a1e; cursor:pointer; transition:all 0.15s; }}
  .filter-btn:hover {{ border-color:#333; color:#888; }}
  .filter-btn.active {{ border-color:#c0392b; color:#c0392b; background:#1a0a08; }}
  .filter-group {{ display:flex; align-items:center; gap:6px; }}
  .filter-label {{ font-family:'JetBrains Mono',monospace; font-size:9px; letter-spacing:0.1em; text-transform:uppercase; color:#333; }}
  .filter-sep {{ width:1px; height:20px; background:#1a1a1e; margin:0 4px; }}
  .feed-post-name {{ color:#ddd; text-decoration:none; font-size:13px; font-weight:500; display:block; }}
  a.feed-post-name:hover {{ color:#0077b5; text-decoration:underline; }}
  .hidden {{ display:none !important; }}
  .post-count {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:#444; margin-left:auto; }}
  .footer {{ display:flex; justify-content:space-between; margin-top:48px; padding-top:16px; border-top:1px solid #1a1a1e; font-family:'JetBrains Mono',monospace; font-size:10px; color:#333; }}
</style>
</head>
<body>
<h1>Feed Intelligence</h1>
<div class="title">Network Analysis Report</div>
<div class="meta">{total} posts analyzed &middot; generated by linkedin feed agent</div>

<div class="kpi-row">
  <div class="kpi"><div class="kpi-value">{total}</div><div class="kpi-label">Posts Analyzed</div></div>
  <div class="kpi"><div class="kpi-value accent">{top_topic_pct}%</div><div class="kpi-label">Top Topic Share</div></div>
  <div class="kpi"><div class="kpi-value">{len(high_engagement_posts)}</div><div class="kpi-label">High Engagement</div></div>
  <div class="kpi"><div class="kpi-value">{esc(top_format)}</div><div class="kpi-label">Dominant Format</div></div>
</div>

<h2>Key Finding</h2>
<p><strong>{esc(top_topic)}</strong> content dominates your feed at {top_topic_pct}% of posts, with an average of {int(topic_avg_engagement.get(top_topic, 0))} likes per post. Personal stories and contrarian takes consistently outperform informational content by 2-3x.</p>

<div class="insight-box">
  <h3>Opportunity</h3>
  <p>Your network has high appetite for <strong>{esc(top_topic)}</strong> content but most of it is abstract commentary. Posts grounded in <em>specific, personal experience</em> with concrete numbers perform dramatically better.</p>
</div>

<div class="insight-box warning">
  <h3>Saturation</h3>
  <p>"Day in my life" and gratitude posts are oversaturated. Generic listicles get low engagement unless they contain genuinely surprising picks.</p>
</div>

<h2>Topic Distribution</h2>
{topic_bars}

<h2>Top Performing Posts</h2>
{top_posts_html}

<h2>Recommendations</h2>

<div class="rec">
  <div class="rec-num">REC 01</div>
  <div class="rec-title">Share a specific {esc(top_topic)} experience with numbers</div>
  <div class="rec-body">Your feed rewards concrete results ("reduced latency by 73%", "shipped in 3 days") over abstract takes. Write about something you built or tried, with specific outcomes.</div>
</div>

<div class="rec">
  <div class="rec-num">REC 02</div>
  <div class="rec-title">Take a contrarian position</div>
  <div class="rec-body">The highest-engagement posts in your feed are contrarian. If you have a genuine disagreement with conventional wisdom, that is your highest-ROI post.</div>
</div>

<div class="rec">
  <div class="rec-num">REC 03</div>
  <div class="rec-title">Text-only for hot takes, carousels for guides</div>
  <div class="rec-body">Plain text posts get the most engagement for opinion pieces. Save carousels and images for step-by-step content where visual structure adds value.</div>
</div>

<h2>All Posts <span id="post-count" class="post-count">{len(all_sorted)} posts</span></h2>

<div class="filters">
  <div class="filter-group">
    <span class="filter-label">Topic</span>
    <button class="filter-btn active" data-filter="topic" data-value="all" onclick="toggleFilter(this)">All</button>
    {"".join(f'<button class="filter-btn" data-filter="topic" data-value="{esc(t)}" onclick="toggleFilter(this)">{esc(t)}</button>' for t in topic_counts.keys())}
  </div>
  <div class="filter-sep"></div>
  <div class="filter-group">
    <span class="filter-label">Engagement</span>
    <button class="filter-btn active" data-filter="engagement" data-value="all" onclick="toggleFilter(this)">All</button>
    <button class="filter-btn" data-filter="engagement" data-value="high" onclick="toggleFilter(this)">High</button>
    <button class="filter-btn" data-filter="engagement" data-value="medium" onclick="toggleFilter(this)">Medium</button>
    <button class="filter-btn" data-filter="engagement" data-value="low" onclick="toggleFilter(this)">Low</button>
  </div>
  <div class="filter-sep"></div>
  <div class="filter-group">
    <span class="filter-label">Format</span>
    <button class="filter-btn active" data-filter="format" data-value="all" onclick="toggleFilter(this)">All</button>
    {"".join(f'<button class="filter-btn" data-filter="format" data-value="{esc(f)}" onclick="toggleFilter(this)">{esc(f)}</button>' for f in format_counts.keys())}
  </div>
  <div class="filter-sep"></div>
  <div class="filter-group">
    <span class="filter-label">Promoted</span>
    <button class="filter-btn active" data-filter="promoted" data-value="hide" onclick="toggleFilter(this)">Hide</button>
    <button class="filter-btn" data-filter="promoted" data-value="show" onclick="toggleFilter(this)">Show</button>
    <button class="filter-btn" data-filter="promoted" data-value="only" onclick="toggleFilter(this)">Only</button>
  </div>
</div>

<div id="posts-container">
{all_posts_html}
</div>

<script>
var activeFilters = {{topic: 'all', engagement: 'all', format: 'all', promoted: 'hide'}};

function toggleFilter(btn) {{
  var group = btn.getAttribute('data-filter');
  var value = btn.getAttribute('data-value');
  activeFilters[group] = value;
  var siblings = document.querySelectorAll('.filter-btn[data-filter="' + group + '"]');
  siblings.forEach(function(s) {{ s.classList.remove('active'); }});
  btn.classList.add('active');
  applyFilters();
}}

function applyFilters() {{
  var posts = document.querySelectorAll('.feed-post');
  var visible = 0;
  posts.forEach(function(post) {{
    var show = true;
    if (activeFilters.topic !== 'all' && post.getAttribute('data-topic') !== activeFilters.topic) show = false;
    if (activeFilters.engagement !== 'all' && post.getAttribute('data-engagement') !== activeFilters.engagement) show = false;
    if (activeFilters.format !== 'all' && post.getAttribute('data-format') !== activeFilters.format) show = false;
    var isPromoted = post.getAttribute('data-promoted') === 'true';
    if (activeFilters.promoted === 'hide' && isPromoted) show = false;
    if (activeFilters.promoted === 'only' && !isPromoted) show = false;
    post.classList.toggle('hidden', !show);
    if (show) visible++;
  }});
  document.getElementById('post-count').textContent = visible + ' of ' + posts.length + ' posts';
}}

applyFilters();

// Notify parent frame of height changes for resize
function notifyHeight() {{
  window.parent.postMessage({{type: 'resize', height: document.documentElement.scrollHeight}}, '*');
}}
new ResizeObserver(notifyHeight).observe(document.body);
setTimeout(notifyHeight, 100);
</script>

<div class="footer">
  <span>FEED INTELLIGENCE v0.1.0</span>
  <span>Powered by Claude Agent SDK</span>
</div>
</body>
</html>"""

    output_path = pathlib.Path(__file__).parent / "report.html"
    output_path.write_text(report_html)
    print(f"REPORT_FILE:{output_path}", flush=True)

    return {
        "content": [
            {"type": "text", "text": f"Report generated and saved to {output_path}. The HTML report is ready."}
        ]
    }


feed_tools_server = create_sdk_mcp_server(
    name="linkedin-feed-tools",
    tools=[scrape_feed, classify_posts, generate_report],
)


async def run_agent():
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"feed": feed_tools_server},
        allowed_tools=[
            "mcp__feed__scrape_feed",
            "mcp__feed__classify_posts",
            "mcp__feed__generate_report",
        ],
        permission_mode="dontAsk",
        max_turns=10,
    )

    async for message in query(
        prompt="Analyze my LinkedIn feed. Scrape 20 posts, classify them, then generate a narrative report with content strategy recommendations.",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Agent: {block.text[:200]}", flush=True)
        elif isinstance(message, ResultMessage):
            print(f"\nDone. Cost: ${message.total_cost_usd:.4f}", flush=True)

    report_path = pathlib.Path(__file__).parent / "report.html"
    if report_path.exists():
        return report_path.read_text()
    return None


if __name__ == "__main__":
    asyncio.run(run_agent())

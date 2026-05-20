"""LinkedIn feed scraper using agent-browser + Chrome Beta CDP."""

import json
import subprocess
import time
import sys
import re

SESSION_FILE = "/tmp/feed-session-id"

EXTRACT_JS = r"""
(function() {
  var menuBtns = document.querySelectorAll('button[aria-label*="control menu"]');
  var posts = [];
  var seen = {};

  menuBtns.forEach(function(btn) {
    var container = btn.parentElement;
    if (container) container = container.parentElement;
    if (!container) return;

    var ariaLabel = btn.getAttribute('aria-label') || '';
    var authorMatch = ariaLabel.match(/post by (.+)/);
    var authorName = authorMatch ? authorMatch[1].trim() : '';

    var fullText = container.innerText || '';
    var lines = fullText.split('\n').map(function(l){return l.trim();}).filter(function(l){return l.length > 0;});

    var headline = '';
    var textLines = [];
    var foundAuthor = false;
    var foundHeadline = false;
    var likes = 0, comments = 0, reposts = 0;
    var inPostBody = false;
    var isPromoted = fullText.indexOf('Promoted') > -1 && lines.indexOf('Promoted') > -1;

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];

      // Parse engagement counts
      var rxMatch = line.match(/^(\d[\d,]*)\s*reactions?$/);
      var cmMatch = line.match(/^(\d[\d,]*)\s*comments?$/);
      var rpMatch = line.match(/^(\d[\d,]*)\s*reposts?$/);
      if (rxMatch) { likes = parseInt(rxMatch[1].replace(/,/g,'')); continue; }
      if (cmMatch) { comments = parseInt(cmMatch[1].replace(/,/g,'')); continue; }
      if (rpMatch) { reposts = parseInt(rpMatch[1].replace(/,/g,'')); continue; }

      if (line === 'Feed post' || line === '…see more' || line === '… more' || line === 'See translation') continue;
      if (/^(Like|Comment|Repost|Send)$/.test(line)) continue;
      if (line === 'Reaction button state: no reaction' || line === 'Follow') continue;
      if (line === 'Promoted') continue;
      if (/^Open reactions menu/.test(line)) continue;

      if (!foundAuthor && line.indexOf(authorName) > -1) { foundAuthor = true; continue; }
      if (foundAuthor && !foundHeadline && /^\d+(st|nd|rd|th)$/.test(line)) continue;
      if (foundAuthor && !foundHeadline && line === '•') continue;

      // Headline: first substantial line after author
      if (foundAuthor && !foundHeadline && line.length > 10) {
        headline = line;
        foundHeadline = true;
        continue;
      }

      // Time indicator marks start of post body
      if (foundHeadline && !inPostBody && /^\d+[hdwmo]\s*•?\s*$/.test(line)) { inPostBody = true; continue; }
      if (foundHeadline && !inPostBody && line === 'Edited') continue;
      if (foundHeadline && !inPostBody && /^Visit my website$/.test(line)) continue;

      // Stop at engagement section
      if (/^\d[\d,]*$/.test(line) && line.length < 8) continue; // bare number (reaction count duplicate)
      if (/This image has content credentials/.test(line)) continue;

      if (inPostBody) textLines.push(line);
    }

    var postText = textLines.join('\n').trim();
    var dedupKey = authorName + '|' + postText.substring(0, 100);
    if (seen[dedupKey]) return;
    seen[dedupKey] = true;
    if (postText.length < 10) return;

    var imgs = container.querySelectorAll('img');
    var mediaImgs = 0;
    imgs.forEach(function(img) {
      var src = img.src || '';
      if (src.indexOf('media') > -1 || src.indexOf('dms') > -1) mediaImgs++;
    });
    var hasVideo = container.querySelector('video') !== null;
    var mediaType = hasVideo ? 'video' : mediaImgs > 1 ? 'carousel' : mediaImgs === 1 ? 'image' : 'text';

    // Grab author profile URL
    var authorLink = '';
    var aLinks = container.querySelectorAll('a[href*="linkedin.com/in/"]');
    if (aLinks.length > 0) authorLink = aLinks[0].getAttribute('href') || '';

    posts.push({
      author_name: authorName,
      author_headline: headline.substring(0, 300),
      author_url: authorLink,
      text: postText.substring(0, 3000),
      likes: likes, comments: comments, reposts: reposts,
      media_type: mediaType, url: '',
      is_promoted: isPromoted,
      timestamp: new Date().toISOString()
    });
  });
  return JSON.stringify(posts);
})()
"""


def run_cmd(args, timeout=30):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip()


def get_session():
    with open(SESSION_FILE) as f:
        return f.read().strip()


def scrape_feed(target_count=200, skip_promoted=True):
    session = get_session()
    base = ["agent-browser", "--cdp", "9222", "--session", session]

    print(f"Navigating to LinkedIn feed... (skip_promoted={skip_promoted})", flush=True)
    run_cmd(base + ["open", "https://www.linkedin.com/feed/"])
    time.sleep(4)

    all_posts = {}
    promoted_count = 0
    scroll_count = 0
    stale_rounds = 0
    max_scrolls = target_count // 2 + 10

    while len(all_posts) < target_count and scroll_count < max_scrolls:
        raw = run_cmd(base + ["eval", EXTRACT_JS])
        if raw.startswith('"') and raw.endswith('"'):
            raw = json.loads(raw)

        try:
            posts = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            posts = []

        prev_count = len(all_posts)
        for post in posts:
            if post.get("is_promoted") and skip_promoted:
                promoted_count += 1
                continue
            key = post["author_name"] + "|" + post["text"][:100]
            if key not in all_posts:
                all_posts[key] = post

        new_count = len(all_posts) - prev_count
        skipped = f" ({promoted_count} promoted skipped)" if promoted_count else ""
        print(f"Scroll {scroll_count + 1}: +{new_count} new ({len(all_posts)} total){skipped}", flush=True)

        if new_count == 0:
            stale_rounds += 1
            if stale_rounds >= 5:
                print("No new posts after 5 scrolls, stopping.", flush=True)
                break
        else:
            stale_rounds = 0

        # Scroll the main feed container (not window)
        run_cmd(base + ["eval", "var m = document.querySelector('main'); if(m) m.scrollBy(0, 3000); else window.scrollBy(0, 3000); 'scrolled'"])
        time.sleep(3)
        scroll_count += 1

    result = list(all_posts.values())
    print(f"Done: {len(result)} unique posts collected", flush=True)
    return result


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    posts = scrape_feed(count)

    output_path = "/Users/glebkalinin/ai_projects/20260512-brainstorm/agent/scraped_posts.json"
    with open(output_path, "w") as f:
        json.dump(posts, f, indent=2, default=str)

    print(f"Saved {len(posts)} posts to {output_path}")

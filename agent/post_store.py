"""Persistent store for scraped LinkedIn posts with deduplication."""

import fcntl
import json
import pathlib
from datetime import datetime

STORE_PATH = pathlib.Path(__file__).parent / "post_history.json"
LOCK_PATH = STORE_PATH.with_suffix(".lock")


def _locked_operation(fn):
    """Run fn with an exclusive file lock on the store."""
    LOCK_PATH.touch(exist_ok=True)
    with open(LOCK_PATH, "r") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return fn()
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load() -> dict[str, dict]:
    if not STORE_PATH.exists():
        return {}
    try:
        return json.loads(STORE_PATH.read_text())
    except (json.JSONDecodeError, ValueError):
        return {}


def _save(store: dict[str, dict]):
    tmp = STORE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, indent=2, default=str))
    tmp.rename(STORE_PATH)


def _dedup_key(post: dict) -> str:
    author = post.get("author_name", "")
    text = post.get("text", "")[:150]
    return f"{author}|{text}"


def add_posts(posts: list[dict]) -> tuple[int, int]:
    """Add posts to store. Returns (new_count, total_count)."""
    def _do():
        store = _load()
        new = 0
        for post in posts:
            key = _dedup_key(post)
            if key not in store:
                post["first_seen"] = datetime.now().isoformat()
                post["seen_count"] = 1
                store[key] = post
                new += 1
            else:
                store[key]["seen_count"] = store[key].get("seen_count", 1) + 1
                store[key]["last_seen"] = datetime.now().isoformat()
                if post.get("likes", 0) > store[key].get("likes", 0):
                    store[key]["likes"] = post["likes"]
                if post.get("comments", 0) > store[key].get("comments", 0):
                    store[key]["comments"] = post["comments"]
                if post.get("reposts", 0) > store[key].get("reposts", 0):
                    store[key]["reposts"] = post["reposts"]
        _save(store)
        return new, len(store)
    return _locked_operation(_do)


def get_all_posts() -> list[dict]:
    """Return all stored posts, newest first."""
    store = _load()
    posts = list(store.values())
    posts.sort(key=lambda p: p.get("first_seen", ""), reverse=True)
    return posts


def get_stats() -> dict:
    store = _load()
    return {
        "total_posts": len(store),
        "store_path": str(STORE_PATH),
    }

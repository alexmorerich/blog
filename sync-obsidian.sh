#!/usr/bin/env bash
# sync-obsidian.sh — Watch an Obsidian Publish/ folder and sync .md files to the blog.
#
# USAGE
#   ./sync-obsidian.sh
#
# CONFIG
#   Set OBSIDIAN_PUBLISH_DIR before running (or edit the default below):
#     OBSIDIAN_PUBLISH_DIR=~/Documents/Obsidian/Publish ./sync-obsidian.sh
#
# DEPENDENCIES
#   fswatch — brew install fswatch   (only external dep)
#   python3 — ships with macOS
#
# DEPLOY FLOW
#   1. Obsidian saves a .md file inside your Publish/ folder
#   2. fswatch fires → frontmatter is normalised → file copied to src/content/blog/
#   3. git commit + push origin main
#   4. Cloudflare picks up the change on `main` and re-deploys automatically

set -uo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
OBSIDIAN_PUBLISH_DIR="${OBSIDIAN_PUBLISH_DIR:-/Users/alexkou/Library/Mobile Documents/iCloud~md~obsidian/Documents/Publish}"
BLOG_DIR="$(cd "$(dirname "$0")" && pwd)"
BLOG_CONTENT_DIR="$BLOG_DIR/src/content/blog"
NORMALIZE="$BLOG_DIR/normalize_frontmatter.py"

# ── Pre-flight ────────────────────────────────────────────────────────────────
if ! command -v fswatch &>/dev/null; then
    echo "[sync] ERROR: fswatch not found. Install: brew install fswatch" >&2
    exit 1
fi

if [[ ! -d "$OBSIDIAN_PUBLISH_DIR" ]]; then
    echo "[sync] ERROR: Publish folder not found: $OBSIDIAN_PUBLISH_DIR" >&2
    echo "[sync]        Set OBSIDIAN_PUBLISH_DIR to your Obsidian Publish folder path." >&2
    exit 1
fi

echo "[sync] Watching : $OBSIDIAN_PUBLISH_DIR"
echo "[sync] Target   : $BLOG_CONTENT_DIR"
echo "[sync] Ready. Ctrl-C to stop."
echo ""

# ── File handler ──────────────────────────────────────────────────────────────
handle_file() {
    local src="$1"
    local filename
    filename="$(basename "$src")"

    # Ignore non-Markdown and deleted files
    [[ "$filename" == *.md ]] || return 0
    [[ -f "$src" ]]           || return 0

    local dest="$BLOG_CONTENT_DIR/$filename"
    local ts
    ts="$(date '+%H:%M:%S')"

    echo "[$ts] ── $filename"

    # Normalize frontmatter and write to blog content dir
    if ! python3 "$NORMALIZE" "$src" "$dest"; then
        echo "[$ts] ERROR: normalization failed — skipping." >&2
        return 0
    fi

    # Stage; skip commit if file content is identical after normalization
    cd "$BLOG_DIR"
    git add "$dest"
    if git diff --cached --quiet; then
        echo "[$ts] No effective change — skipped commit."
        return 0
    fi

    git commit -m "sync: $filename"

    if git push origin main; then
        echo "[$ts] Pushed → GitHub (Cloudflare deploy triggered)"
    else
        echo "[$ts] WARNING: push failed — changes committed locally, retry manually." >&2
    fi
}

# ── Watch loop ────────────────────────────────────────────────────────────────
# -0   NUL-delimit output (handles filenames with spaces)
# -l 2 2-second latency window — batches Obsidian's rapid auto-saves
fswatch -0 -l 2 \
    --event Created \
    --event Updated \
    --event Renamed \
    "$OBSIDIAN_PUBLISH_DIR" \
| while IFS= read -r -d $'\0' changed_file; do
    handle_file "$changed_file" || true
done

#!/bin/bash
# Agent 작업 종료 시 변경사항을 GitHub에 자동 커밋/푸시합니다.

set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

REMOTE="origin"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  exit 0
fi

if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  exit 0
fi

git add -A

MSG="chore: auto-sync $(date '+%Y-%m-%d %H:%M:%S')"
git commit -m "$MSG" || exit 0

git push "$REMOTE" "$BRANCH" 2>/dev/null || git push -u "$REMOTE" "$BRANCH"

exit 0

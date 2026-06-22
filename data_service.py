import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import requests

YAGOONARA_BASE = "https://www.yagoonara.com/api"
SSG_TEAM_ID = 7
MIN_SEASON = 2000
MAX_SEASON = 2026

_players_cache: Dict[str, Any] = {"data": None, "expires": 0.0}
_player_detail_cache: Dict[int, Dict[str, Any]] = {}
_season_stats_cache: Dict[str, Dict[str, Any]] = {}

CACHE_TTL = 60 * 60  # 1 hour


def _get_json(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    response = requests.get(
        f"{YAGOONARA_BASE}{path}",
        params=params,
        headers={"User-Agent": "SSG-Landers-Stats-MVP/1.0"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"API error: {path}")
    return payload.get("data")


def get_ssg_players() -> List[Dict[str, Any]]:
    now = time.time()
    if _players_cache["data"] and _players_cache["expires"] > now:
        return _players_cache["data"]

    players = _get_json("/players", {"team": "ssg", "limit": 500})
    players.sort(key=lambda p: p.get("name", ""))
    _players_cache["data"] = players
    _players_cache["expires"] = now + CACHE_TTL
    return players


def search_players(query: str) -> List[Dict[str, Any]]:
    query = query.strip().lower()
    players = get_ssg_players()
    if not query:
        return players[:30]

    matched = []
    for player in players:
        name = player.get("name", "")
        name_en = (player.get("name_en") or "").lower()
        back_number = str(player.get("back_number") or "")
        if query in name.lower() or query in name_en or query == back_number:
            matched.append(player)
    return matched[:30]


def get_player_detail(player_id: int) -> Dict[str, Any]:
    now = time.time()
    cached = _player_detail_cache.get(player_id)
    if cached and cached["expires"] > now:
        return cached["data"]

    data = _get_json(f"/players/{player_id}")
    _player_detail_cache[player_id] = {"data": data, "expires": now + CACHE_TTL}
    return data


def _filter_regular_kbo(stats: List[Dict[str, Any]], year: int) -> Optional[Dict[str, Any]]:
    for stat in stats:
        if (
            stat.get("year") == year
            and stat.get("team_id") == SSG_TEAM_ID
            and stat.get("game_type") == "regular"
            and stat.get("league_type") == "kbo"
        ):
            return stat
    return None


def _fetch_player_season_row(player: Dict[str, Any], year: int, stat_type: str) -> Optional[Dict[str, Any]]:
    detail = get_player_detail(player["id"])
    stats_key = "hitter_stats" if stat_type == "hitter" else "pitcher_stats"
    stat = _filter_regular_kbo(detail.get(stats_key, []), year)
    if not stat:
        return None

    row = {
        "player_id": player["id"],
        "name": player.get("name"),
        "back_number": player.get("back_number"),
        "position": player.get("position"),
    }
    row.update(stat)
    return row


def get_season_stats(year: int, stat_type: str) -> List[Dict[str, Any]]:
    if year < MIN_SEASON or year > MAX_SEASON:
        raise ValueError(f"시즌은 {MIN_SEASON}~{MAX_SEASON}년만 조회할 수 있습니다.")

    if stat_type not in {"hitter", "pitcher"}:
        raise ValueError("stat_type은 hitter 또는 pitcher여야 합니다.")

    cache_key = f"{year}:{stat_type}"
    now = time.time()
    cached = _season_stats_cache.get(cache_key)
    if cached and cached["expires"] > now:
        return cached["data"]

    players = get_ssg_players()
    rows: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(_fetch_player_season_row, player, year, stat_type): player
            for player in players
        }
        for future in as_completed(futures):
            try:
                row = future.result()
                if row:
                    rows.append(row)
            except Exception:
                continue

    if stat_type == "hitter":
        rows.sort(key=lambda r: float(r.get("ops") or 0), reverse=True)
    else:
        rows.sort(key=lambda r: float(r.get("era") or 999))

    _season_stats_cache[cache_key] = {"data": rows, "expires": now + CACHE_TTL}
    return rows

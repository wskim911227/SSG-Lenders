import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import requests

YAGOONARA_BASE = "https://www.yagoonara.com/api"
DEFAULT_TEAM_ID = 7
MIN_SEASON = 2000
MAX_SEASON = 2026

_players_cache: Dict[int, Dict[str, Any]] = {}
_player_detail_cache: Dict[int, Dict[str, Any]] = {}
_season_stats_cache: Dict[str, Dict[str, Any]] = {}
_teams_cache: Dict[str, Any] = {"data": None, "expires": 0.0}

CACHE_TTL = 60 * 60  # 1 hour


def _get_json(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    response = requests.get(
        f"{YAGOONARA_BASE}{path}",
        params=params,
        headers={"User-Agent": "KBO-Team-Stats-MVP/1.0"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"API error: {path}")
    return payload.get("data")


def _team_slug(team: Dict[str, Any]) -> str:
    name = team.get("name", "")
    if name.isascii():
        return name.lower()
    return name


def get_teams() -> List[Dict[str, Any]]:
    now = time.time()
    if _teams_cache["data"] and _teams_cache["expires"] > now:
        return _teams_cache["data"]

    teams = _get_json("/teams")
    kbo_teams = [
        {
            "id": team["id"],
            "name": team.get("name"),
            "full_name": team.get("full_name") or team.get("name"),
            "slug": _team_slug(team),
        }
        for team in teams
        if team.get("team_type") == "kbo"
    ]
    kbo_teams.sort(key=lambda team: team["full_name"])

    _teams_cache["data"] = kbo_teams
    _teams_cache["expires"] = now + CACHE_TTL
    return kbo_teams


def get_team(team_id: int) -> Dict[str, Any]:
    for team in get_teams():
        if team["id"] == team_id:
            return team
    raise ValueError("존재하지 않는 구단입니다.")


def get_team_players(team_id: int) -> List[Dict[str, Any]]:
    now = time.time()
    cached = _players_cache.get(team_id)
    if cached and cached["expires"] > now:
        return cached["data"]

    team = get_team(team_id)
    players = _get_json("/players", {"team": team["slug"], "limit": 500})
    players.sort(key=lambda player: player.get("name", ""))

    _players_cache[team_id] = {"data": players, "expires": now + CACHE_TTL}
    return players


def search_players(query: str, team_id: int = DEFAULT_TEAM_ID) -> List[Dict[str, Any]]:
    query = query.strip().lower()
    players = get_team_players(team_id)
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


def _filter_regular_kbo(
    stats: List[Dict[str, Any]], year: int, team_id: int
) -> Optional[Dict[str, Any]]:
    for stat in stats:
        if (
            stat.get("year") == year
            and stat.get("team_id") == team_id
            and stat.get("game_type") == "regular"
            and stat.get("league_type") == "kbo"
        ):
            return stat
    return None


def _fetch_player_season_row(
    player: Dict[str, Any], year: int, stat_type: str, team_id: int
) -> Optional[Dict[str, Any]]:
    detail = get_player_detail(player["id"])
    stats_key = "hitter_stats" if stat_type == "hitter" else "pitcher_stats"
    stat = _filter_regular_kbo(detail.get(stats_key, []), year, team_id)
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


def get_season_stats(
    year: int, stat_type: str, team_id: int = DEFAULT_TEAM_ID
) -> List[Dict[str, Any]]:
    if year < MIN_SEASON or year > MAX_SEASON:
        raise ValueError(f"시즌은 {MIN_SEASON}~{MAX_SEASON}년만 조회할 수 있습니다.")

    if stat_type not in {"hitter", "pitcher"}:
        raise ValueError("stat_type은 hitter 또는 pitcher여야 합니다.")

    get_team(team_id)

    cache_key = f"{team_id}:{year}:{stat_type}"
    now = time.time()
    cached = _season_stats_cache.get(cache_key)
    if cached and cached["expires"] > now:
        return cached["data"]

    players = get_team_players(team_id)
    rows: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(_fetch_player_season_row, player, year, stat_type, team_id): player
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
        rows.sort(key=lambda row: float(row.get("ops") or 0), reverse=True)
    else:
        rows.sort(key=lambda row: float(row.get("era") or 999))

    _season_stats_cache[cache_key] = {"data": rows, "expires": now + CACHE_TTL}
    return rows

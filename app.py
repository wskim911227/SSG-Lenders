from flask import Flask, jsonify, render_template, request

from data_service import (
    DEFAULT_TEAM_ID,
    MAX_SEASON,
    MIN_SEASON,
    get_player_detail,
    get_season_stats,
    get_teams,
    search_players,
)

app = Flask(__name__)


def _parse_team_id() -> int:
    team_id = request.args.get("team_id", DEFAULT_TEAM_ID)
    return int(team_id)


@app.route("/")
def index():
    return render_template(
        "index.html",
        min_season=MIN_SEASON,
        max_season=MAX_SEASON,
        default_team_id=DEFAULT_TEAM_ID,
    )


@app.route("/api/teams")
def api_teams():
    teams = get_teams()
    return jsonify({"success": True, "data": teams})


@app.route("/api/players/search")
def api_search_players():
    try:
        query = request.args.get("q", "")
        team_id = _parse_team_id()
        players = search_players(query, team_id)
        return jsonify(
            {
                "success": True,
                "team_id": team_id,
                "data": [
                    {
                        "id": player["id"],
                        "name": player.get("name"),
                        "back_number": player.get("back_number"),
                        "position": player.get("position"),
                        "is_active": player.get("is_active"),
                    }
                    for player in players
                ],
            }
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/players/<int:player_id>")
def api_player_detail(player_id: int):
    detail = get_player_detail(player_id)
    return jsonify({"success": True, "data": detail})


@app.route("/api/stats")
def api_season_stats():
    try:
        year = int(request.args.get("year", MAX_SEASON))
        stat_type = request.args.get("type", "hitter")
        team_id = _parse_team_id()
        team = next((item for item in get_teams() if item["id"] == team_id), None)
        rows = get_season_stats(year, stat_type, team_id)
        return jsonify(
            {
                "success": True,
                "year": year,
                "type": stat_type,
                "team_id": team_id,
                "team_name": team["full_name"] if team else "",
                "data": rows,
            }
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)

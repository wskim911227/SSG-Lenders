from flask import Flask, jsonify, render_template, request

from data_service import (
    MAX_SEASON,
    MIN_SEASON,
    get_player_detail,
    get_season_stats,
    search_players,
)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template(
        "index.html",
        min_season=MIN_SEASON,
        max_season=MAX_SEASON,
    )


@app.route("/api/players/search")
def api_search_players():
    query = request.args.get("q", "")
    players = search_players(query)
    return jsonify(
        {
            "success": True,
            "data": [
                {
                    "id": p["id"],
                    "name": p.get("name"),
                    "back_number": p.get("back_number"),
                    "position": p.get("position"),
                    "is_active": p.get("is_active"),
                }
                for p in players
            ],
        }
    )


@app.route("/api/players/<int:player_id>")
def api_player_detail(player_id: int):
    detail = get_player_detail(player_id)
    return jsonify({"success": True, "data": detail})


@app.route("/api/stats")
def api_season_stats():
    try:
        year = int(request.args.get("year", MAX_SEASON))
        stat_type = request.args.get("type", "hitter")
        rows = get_season_stats(year, stat_type)
        return jsonify({"success": True, "year": year, "type": stat_type, "data": rows})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)

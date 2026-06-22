const { minSeason, maxSeason } = window.APP_CONFIG;

const seasonSelect = document.getElementById("seasonSelect");
const loadSeasonBtn = document.getElementById("loadSeasonBtn");
const tabs = document.querySelectorAll(".tab");
const playerSearch = document.getElementById("playerSearch");
const searchResults = document.getElementById("searchResults");
const statsTitle = document.getElementById("statsTitle");
const statsCount = document.getElementById("statsCount");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");
const statsHead = document.getElementById("statsHead");
const statsBody = document.getElementById("statsBody");
const playerSection = document.getElementById("playerSection");
const playerTitle = document.getElementById("playerTitle");
const playerMeta = document.getElementById("playerMeta");
const playerHead = document.getElementById("playerHead");
const playerBody = document.getElementById("playerBody");
const closePlayerBtn = document.getElementById("closePlayerBtn");

let currentType = "hitter";
let searchTimer = null;

const HITTER_COLUMNS = [
  ["name", "선수"],
  ["back_number", "등번호"],
  ["position", "포지션"],
  ["games", "경기"],
  ["pa", "타석"],
  ["avg", "타율"],
  ["hr", "홈런"],
  ["rbi", "타점"],
  ["ops", "OPS"],
  ["war", "WAR"],
];

const PITCHER_COLUMNS = [
  ["name", "선수"],
  ["back_number", "등번호"],
  ["position", "포지션"],
  ["games", "경기"],
  ["wins", "승"],
  ["losses", "패"],
  ["saves", "세"],
  ["holds", "홀드"],
  ["innings", "이닝"],
  ["era", "ERA"],
  ["whip", "WHIP"],
  ["so", "삼진"],
  ["war", "WAR"],
];

const PLAYER_HITTER_COLUMNS = [
  ["year", "시즌"],
  ["games", "경기"],
  ["avg", "타율"],
  ["hr", "홈런"],
  ["rbi", "타점"],
  ["ops", "OPS"],
  ["war", "WAR"],
];

const PLAYER_PITCHER_COLUMNS = [
  ["year", "시즌"],
  ["games", "경기"],
  ["wins", "승"],
  ["losses", "패"],
  ["saves", "세"],
  ["holds", "홀드"],
  ["innings", "이닝"],
  ["era", "ERA"],
  ["whip", "WHIP"],
  ["war", "WAR"],
];

function initSeasonSelect() {
  for (let year = maxSeason; year >= minSeason; year -= 1) {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = `${year} 시즌`;
    seasonSelect.appendChild(option);
  }
}

function setLoading(isLoading) {
  loading.classList.toggle("hidden", !isLoading);
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.toggle("hidden", !message);
}

function renderTable(headEl, bodyEl, columns, rows, clickableName = true) {
  headEl.innerHTML = `<tr>${columns.map(([, label]) => `<th>${label}</th>`).join("")}</tr>`;

  bodyEl.innerHTML = rows
    .map((row) => {
      const cells = columns
        .map(([key]) => {
          if (key === "name" && clickableName && row.player_id) {
            return `<td><a href="#" class="player-link" data-player-id="${row.player_id}">${row.name ?? "-"}</a></td>`;
          }
          const value = row[key];
          return `<td>${value ?? "-"}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  if (clickableName) {
    bodyEl.querySelectorAll(".player-link").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        loadPlayerDetail(link.dataset.playerId);
      });
    });
  }
}

async function loadSeasonStats() {
  const year = seasonSelect.value;
  showError("");
  setLoading(true);

  try {
    const response = await fetch(`/api/stats?year=${year}&type=${currentType}`);
    const payload = await response.json();

    if (!payload.success) {
      throw new Error(payload.error || "성적을 불러오지 못했습니다.");
    }

    const columns = currentType === "hitter" ? HITTER_COLUMNS : PITCHER_COLUMNS;
    statsTitle.textContent = `${year} 시즌 ${currentType === "hitter" ? "타자" : "투수"} 성적`;
    statsCount.textContent = `${payload.data.length}명`;
    renderTable(statsHead, statsBody, columns, payload.data);
  } catch (error) {
    showError(error.message);
    statsBody.innerHTML = "";
    statsCount.textContent = "0명";
  } finally {
    setLoading(false);
  }
}

async function searchPlayers(query) {
  const response = await fetch(`/api/players/search?q=${encodeURIComponent(query)}`);
  const payload = await response.json();
  return payload.data || [];
}

function renderSearchResults(players) {
  if (!players.length) {
    searchResults.innerHTML = `<div class="search-item">검색 결과가 없습니다.</div>`;
    searchResults.classList.remove("hidden");
    return;
  }

  searchResults.innerHTML = players
    .map(
      (player) => `
      <button class="search-item" data-player-id="${player.id}">
        <strong>#${player.back_number ?? "-"} ${player.name}</strong>
        <div style="color:#9ca3af;font-size:0.85rem">${player.position ?? "포지션 미상"}${player.is_active ? " · 현역" : ""}</div>
      </button>
    `
    )
    .join("");

  searchResults.querySelectorAll(".search-item[data-player-id]").forEach((item) => {
    item.addEventListener("click", () => {
      searchResults.classList.add("hidden");
      playerSearch.value = item.querySelector("strong").textContent.replace(/^#\S+\s*/, "");
      loadPlayerDetail(item.dataset.playerId);
    });
  });

  searchResults.classList.remove("hidden");
}

async function loadPlayerDetail(playerId) {
  setLoading(true);
  showError("");

  try {
    const response = await fetch(`/api/players/${playerId}`);
    const payload = await response.json();

    if (!payload.success) {
      throw new Error("선수 정보를 불러오지 못했습니다.");
    }

    const player = payload.data;
    const isPitcher = (player.position || "").includes("투수");
    const stats = (isPitcher ? player.pitcher_stats : player.hitter_stats || []).filter(
      (stat) => stat.team_id === 7 && stat.game_type === "regular" && stat.league_type === "kbo"
    );
    stats.sort((a, b) => b.year - a.year);

    playerTitle.textContent = `#${player.back_number ?? "-"} ${player.name}`;
    playerMeta.innerHTML = [
      ["포지션", player.position || "-"],
      ["투타", `${player.throws || "-"} / ${player.bats || "-"}`],
      ["신장/체중", `${player.height || "-"}cm / ${player.weight || "-"}kg`],
      ["연봉", player.salary || "-"],
    ]
      .map(
        ([label, value]) => `
        <div class="meta-item">
          <span>${label}</span>
          <strong>${value}</strong>
        </div>
      `
      )
      .join("");

    const columns = isPitcher ? PLAYER_PITCHER_COLUMNS : PLAYER_HITTER_COLUMNS;
    renderTable(playerHead, playerBody, columns, stats, false);
    playerSection.classList.remove("hidden");
    playerSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
  }
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    currentType = tab.dataset.type;
    loadSeasonStats();
  });
});

loadSeasonBtn.addEventListener("click", loadSeasonStats);

playerSearch.addEventListener("input", () => {
  clearTimeout(searchTimer);
  const query = playerSearch.value.trim();
  if (!query) {
    searchResults.classList.add("hidden");
    return;
  }

  searchTimer = setTimeout(async () => {
    const players = await searchPlayers(query);
    renderSearchResults(players);
  }, 250);
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".search-wrap")) {
    searchResults.classList.add("hidden");
  }
});

closePlayerBtn.addEventListener("click", () => {
  playerSection.classList.add("hidden");
});

initSeasonSelect();
loadSeasonStats();

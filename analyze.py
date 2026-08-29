"""
Kyler Murray vs. The Discord Notification: does a Call of Duty launch
weekend or Double XP weekend line up with better or worse quarterback play?

This script:
1. Loads Kyler Murray's 2024 game log
2. Loads a hand-verified list of 2024 CoD "gaming event" windows
   (Black Ops 6 launch weekend + every announced Double XP weekend)
3. Flags each game as GAMING WEEK or REGULAR WEEK based on whether
   game day fell inside (or the day after) a gaming event window
4. Compares per-game averages between the two buckets
5. Saves two charts + a text summary to charts/ and prints results
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
CHARTS = BASE / "charts"
CHARTS.mkdir(exist_ok=True)

# ---------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------
games = pd.read_csv(DATA / "kyler_murray_2024_gamelog.csv", parse_dates=["date"])
events = pd.read_csv(
    DATA / "gaming_events_2024.csv", parse_dates=["start_date", "end_date"]
)

# ---------------------------------------------------------------
# 2. Flag each game
# A game "counts" as a gaming week if game day falls within an event
# window, OR within 1 day after it closes (Sunday games following a
# Fri-Mon event, hangover effect included on purpose).
# ---------------------------------------------------------------
def in_gaming_week(game_date, events_df):
    for _, ev in events_df.iterrows():
        window_end = ev["end_date"] + pd.Timedelta(days=1)
        if ev["start_date"] <= game_date <= window_end:
            return ev["event_name"]
    return None

games["gaming_event"] = games["date"].apply(lambda d: in_gaming_week(d, events))
games["bucket"] = games["gaming_event"].apply(
    lambda x: "Gaming Week" if pd.notna(x) else "Regular Week"
)

# ---------------------------------------------------------------
# 3. Compute comparison stats
# ---------------------------------------------------------------
games["win"] = (games["result"] == "W").astype(int)

metrics = {
    "Passer Rating": "rating",
    "Pass Yards/Game": "pass_yds",
    "Completion %": "pct",
    "Pass TD/Game": "pass_td",
    "INT/Game": "intercept",
    "Win %": "win",
}

summary = games.groupby("bucket")[list(metrics.values())].mean().round(2)
summary["games"] = games.groupby("bucket").size()
summary = summary.rename(columns={v: k for k, v in metrics.items()})
summary["Win %"] = (summary["Win %"] * 100).round(1)

print("=" * 70)
print("KYLER MURRAY 2024: GAMING WEEKS vs REGULAR WEEKS")
print("=" * 70)
print(summary.to_string())
print()

gaming_games = games[games["bucket"] == "Gaming Week"][
    ["date", "opp", "result", "pass_yds", "pass_td", "intercept", "rating", "gaming_event"]
]
print("Games flagged as 'Gaming Weeks':")
print(gaming_games.to_string(index=False))
print()

# ---------------------------------------------------------------
# 4. Charts
# ---------------------------------------------------------------
plt.style.use("seaborn-v0_8-darkgrid")

# Chart 1: Passer rating per game, color-coded, with event windows shaded
fig, ax = plt.subplots(figsize=(12, 6))
colors = games["bucket"].map({"Gaming Week": "#e63946", "Regular Week": "#457b9d"})
ax.bar(games["date"].dt.strftime("%-m/%-d"), games["rating"], color=colors)
ax.axhline(games["rating"].mean(), color="gray", linestyle="--", linewidth=1,
           label=f"Season avg rating ({games['rating'].mean():.1f})")
ax.set_title("Kyler Murray 2024 Passer Rating by Game\n(Red = CoD launch / Double XP weekend)")
ax.set_ylabel("Passer Rating")
ax.set_xlabel("Game Date")
plt.xticks(rotation=45)
ax.legend()
plt.tight_layout()
plt.savefig(CHARTS / "rating_by_game.png", dpi=150)
plt.close()

# Chart 2: Grouped bar comparison across key metrics (normalized to season avg = 100)
fig, ax = plt.subplots(figsize=(9, 6))
labels = ["Passer Rating", "Pass Yards/Game", "Completion %", "Pass TD/Game", "INT/Game", "Win %"]
gaming_vals = summary.loc["Gaming Week", labels].values
regular_vals = summary.loc["Regular Week", labels].values

x = range(len(labels))
width = 0.35
ax.bar([i - width / 2 for i in x], gaming_vals, width, label="Gaming Week", color="#e63946")
ax.bar([i + width / 2 for i in x], regular_vals, width, label="Regular Week", color="#457b9d")
ax.set_xticks(list(x))
ax.set_xticklabels(labels, rotation=20, ha="right")
ax.set_title("Kyler Murray 2024: Gaming Weeks vs Regular Weeks")
ax.legend()
for i, (g, r) in enumerate(zip(gaming_vals, regular_vals)):
    ax.text(i - width / 2, g, f"{g:.1f}", ha="center", va="bottom", fontsize=8)
    ax.text(i + width / 2, r, f"{r:.1f}", ha="center", va="bottom", fontsize=8)
plt.tight_layout()
plt.savefig(CHARTS / "comparison_bars.png", dpi=150)
plt.close()

print(f"Charts saved to {CHARTS}/")

# Save summary table to CSV for the README / repo
summary.to_csv(BASE / "data" / "summary_output.csv")

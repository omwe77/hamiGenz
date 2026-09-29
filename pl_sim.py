#!/usr/bin/env python3
"""
PREMIER LEAGUE 2024/25 — POISSON + ELO MONTE CARLO SIMULATION (VECTORIZED)
===========================================================================
Model:   Poisson goal distribution + Elo-adjusted team strengths
Dataset: Premier League 2024/25 final table (380 matches, 20 clubs)
Seed:    847291
Runs:    10,000
"""

import numpy as np
import json

# ── SEED ──────────────────────────────────────────────────────────────────────
SEED = 847291
rng = np.random.default_rng(SEED)

# ── DATASET: PREMIER LEAGUE 2024/25 FINAL TABLE ──────────────────────────────
TEAMS = [
    "Liverpool", "Arsenal", "Manchester City", "Chelsea",
    "Newcastle United", "Aston Villa", "Nottingham Forest", "Brighton",
    "Bournemouth", "Brentford", "Fulham", "Crystal Palace",
    "Everton", "West Ham United", "Manchester United", "Wolves",
    "Tottenham Hotspur", "Leicester City", "Ipswich Town", "Southampton",
]

# P, W, D, L, GF, GA, Pts  (from official final table)
SEASON = [
    (38, 25, 9,  4,  86, 41, 84),   # Liverpool
    (38, 20, 14, 4,  69, 34, 74),   # Arsenal
    (38, 21, 8,  9,  72, 44, 71),   # Man City
    (38, 20, 9,  9,  64, 43, 69),   # Chelsea
    (38, 20, 6,  12, 68, 47, 66),   # Newcastle
    (38, 19, 9,  10, 58, 51, 66),   # Aston Villa
    (38, 19, 8,  11, 58, 46, 65),   # Nottm Forest
    (38, 16, 13, 9,  66, 59, 61),   # Brighton
    (38, 15, 11, 12, 58, 46, 56),   # Bournemouth
    (38, 16, 8,  14, 66, 57, 56),   # Brentford
    (38, 15, 9,  14, 54, 54, 54),   # Fulham
    (38, 13, 14, 11, 51, 51, 53),   # Crystal Palace
    (38, 11, 15, 12, 42, 44, 48),   # Everton
    (38, 11, 10, 17, 46, 62, 43),   # West Ham
    (38, 11, 9,  18, 44, 54, 42),   # Man Utd
    (38, 12, 6,  20, 54, 69, 42),   # Wolves
    (38, 11, 5,  22, 64, 65, 38),   # Tottenham
    (38, 6,  7,  25, 33, 80, 25),   # Leicester
    (38, 4,  10, 24, 36, 82, 22),   # Ipswich
    (38, 2,  6,  30, 26, 86, 12),   # Southampton
]

N = len(TEAMS)
PPG_LEAGUE = sum(s[6] for s in SEASON) / (N * 38)  # ~2.525

# Attack/Defense strengths (league avg = 1.0)
ATTACK = np.array([s[4] / 38 / (sum(s[4] for s in SEASON) / (N * 38)) for s in SEASON])
DEFENSE = np.array([s[5] / 38 / (sum(s[5] for s in SEASON) / (N * 38)) for s in SEASON])

# Elo ratings: linear map from PPG to [1400, 2250]
MIN_PPG = min(s[6] / 38 for s in SEASON)
MAX_PPG = max(s[6] / 38 for s in SEASON)
ELO = np.array([
    1400 + (s[6] / 38 - MIN_PPG) / (MAX_PPG - MIN_PPG) * 850
    for s in SEASON
])

HOME_ADV = 0.30  # goals

# Pre-compute Elo factors for all pairs (N x N matrix)
# elo_factor[i,j] = 10^((ELO[i] - ELO[j]) / 100 * 0.08)
ELO_DIFF = (ELO[:, None] - ELO[None, :]) / 100.0
ELO_FACTOR_HOME = 10 ** (ELO_DIFF * 0.08)   # N x N: how much home team gains from Elo
ELO_FACTOR_AWAY = 10 ** (-ELO_DIFF * 0.08)  # N x N: how much away team gains

# Expected goals matrix (N x N): lambda_home[i,j] = expected goals when i hosts j
LAMBDA_HOME = ATTACK[:, None] * DEFENSE[None, :] * ELO_FACTOR_HOME + HOME_ADV
LAMBDA_AWAY  = ATTACK[None, :] * DEFENSE[:, None] * ELO_FACTOR_AWAY

print(f"Teams: {N}")
print(f"League avg PPG: {PPG_LEAGUE:.3f}")
print(f"Attack range: [{ATTACK.min():.3f}, {ATTACK.max():.3f}]")
print(f"Defense range: [{DEFENSE.min():.3f}, {DEFENSE.max():.3f}]")
print(f"Elo range: [{ELO.min():.0f}, {ELO.max():.0f}]")
print(f"Lambda home range: [{LAMBDA_HOME.min():.2f}, {LAMBDA_HOME.max():.2f}]")
print(f"Lambda away range: [{LAMBDA_AWAY.min():.2f}, {LAMBDA_AWAY.max():.2f}]")
print()

# ── FIXTURE SCHEDULE ──────────────────────────────────────────────────────────
# Double round-robin: 38 rounds × 10 matches = 380 matches
# Each pair (i,j) plays twice: i@home and j@home
# Build indices for vectorized simulation

# fixture_home[i] = index of home team for fixture i
# fixture_away[i] = index of away team for fixture i
fixture_home = []
fixture_away = []

for i in range(N):
    for j in range(N):
        if i != j:
            fixture_home.append(i)
            fixture_away.append(j)

fixture_home = np.array(fixture_home)   # 380 matches
fixture_away = np.array(fixture_away)

# Group into 38 rounds (each team plays once per round)
# Simple approach: assign each fixture to a round such that no team plays twice in a round
# We'll use a standard round-robin generation

def build_round_robin_schedule(n_teams):
    """Generate 38 rounds of 10 matches each (double round-robin)."""
    n = n_teams
    rounds = []
    # Single round-robin: n-1 rounds
    teams = list(range(n))
    for r in range(n - 1):
        round_matches = []
        for k in range(n // 2):
            home = teams[k]
            away = teams[n - 1 - k]
            round_matches.append((home, away))
        rounds.append(round_matches)
        # Rotate: keep teams[0] fixed, rotate rest
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    # Double: repeat with reversed home/away
    double_rounds = []
    for r_matches in rounds:
        double_rounds.append(r_matches)
    for r_matches in rounds:
        double_rounds.append([(away, home) for home, away in r_matches])
    return double_rounds

schedule = build_round_robin_schedule(N)
assert len(schedule) == 38
for r in schedule:
    assert len(r) == 10

# Convert to arrays for fast indexing
ROUND_HOME = np.array([[h for h, a in round_matches] for round_matches in schedule])  # 38×10
ROUND_AWAY = np.array([[a for h, a in round_matches] for round_matches in schedule])  # 38×10

print(f"Schedule: {len(schedule)} rounds × {len(schedule[0])} matches = {len(schedule) * len(schedule[0])} matches")
print()

# ── VECTORIZED SIMULATION ─────────────────────────────────────────────────────
N_RUNS = 10_000

# Storage
title_wins = np.zeros(N, dtype=int)
top4 = np.zeros(N, dtype=int)
top6 = np.zeros(N, dtype=int)
relegation = np.zeros(N, dtype=int)
all_points = np.zeros((N_RUNS, N), dtype=np.int16)
all_gd = np.zeros((N_RUNS, N), dtype=np.int16)
all_gf = np.zeros((N_RUNS, N), dtype=np.int16)
all_ga = np.zeros((N_RUNS, N), dtype=np.int16)

print(f"Running {N_RUNS:,} simulations...")
print("-" * 52)

for run in range(N_RUNS):
    if (run + 1) % 2000 == 0:
        print(f"  Run {run + 1}/{N_RUNS}...", end="\r")

    # Points tracker per team
    pts = np.zeros(N, dtype=np.int16)
    gf = np.zeros(N, dtype=np.int16)
    ga = np.zeros(N, dtype=np.int16)

    # Run all 38 rounds
    for rnd in range(38):
        h = ROUND_HOME[rnd]   # 10 home team indices
        a = ROUND_AWAY[rnd]   # 10 away team indices

        # Poisson draws for this round's 10 matches (advanced indexing into N×N matrices)
        hg = rng.poisson(LAMBDA_HOME[h, a])  # home goals
        ag = rng.poisson(LAMBDA_AWAY[h, a])  # away goals

        # Update stats
        for k in range(10):
            hi = h[k]
            ai = a[k]
            gh = hg[k]
            ga_ = ag[k]

            gf[hi] += gh
            ga[hi] += ga_
            gf[ai] += ga_
            ga[ai] += gh

            if gh > ga_:
                pts[hi] += 3
            elif ga_ > gh:
                pts[ai] += 3
            else:
                pts[hi] += 1
                pts[ai] += 1

    # Record
    all_points[run] = pts
    all_gd[run] = gf - ga
    all_gf[run] = gf
    all_ga[run] = ga

    # Rank and tally
    # Sort by points (desc), then GD (desc)
    order = np.lexsort((all_gd[run], all_points[run]))[::-1]  # indices sorted by pts then gd

    for pos, team_idx in enumerate(order):
        pos1 = pos + 1
        if pos1 == 1:
            title_wins[team_idx] += 1
        if pos1 <= 4:
            top4[team_idx] += 1
        if pos1 <= 6:
            top6[team_idx] += 1
        if pos1 >= 18:
            relegation[team_idx] += 1

print(f"\n  Completed {N_RUNS:,} runs.")
print()

# ── RESULTS ───────────────────────────────────────────────────────────────────
def pct(x): return f"{x / N_RUNS * 100:.2f}%"

print("=" * 70)
print(f"  PREMIER LEAGUE 2024/25 — POISSON + ELO SIMULATION")
print(f"  Seed: {SEED}  |  Runs: {N_RUNS:,}  |  Model: Poisson + Elo")
print("=" * 70)
print()

# Champion
print("  CHAMPION (title win %)")
print("  " + "-" * 50)
title_order = np.argsort(title_wins)[::-1]
for ti in title_order:
    bar = "█" * int(title_wins[ti] / N_RUNS * 100)
    print(f"  {TEAMS[ti]:<22} {pct(title_wins[ti]):>8}  {bar}")
print()

# Top 4
print("  TOP 4 FINISHES (%)")
print("  " + "-" * 50)
for ti in np.argsort(top4)[::-1]:
    bar = "█" * int(top4[ti] / N_RUNS * 100)
    print(f"  {TEAMS[ti]:<22} {pct(top4[ti]):>8}  {bar}")
print()

# Top 6
print("  TOP 6 FINISHES (%)")
print("  " + "-" * 50)
for ti in np.argsort(top6)[::-1]:
    bar = "█" * int(top6[ti] / N_RUNS * 100)
    print(f"  {TEAMS[ti]:<22} {pct(top6[ti]):>8}  {bar}")
print()

# Relegation
print("  RELEGATION RISK (%) — 18th–20th place")
print("  " + "-" * 50)
for ti in np.argsort(relegation)[::-1]:
    if relegation[ti] > 0:
        bar = "█" * int(relegation[ti] / N_RUNS * 100)
        print(f"  {TEAMS[ti]:<22} {pct(relegation[ti]):>8}  {bar}")
print()

# Expected points
print("  EXPECTED POINTS (mean ± std, median, range)")
print("  " + "-" * 55)
pts_mean = all_points.mean(axis=0)
pts_std = all_points.std(axis=0)
pts_med = np.median(all_points, axis=0)
pts_min = all_points.min(axis=0)
pts_max = all_points.max(axis=0)

order = np.argsort(pts_mean)[::-1]
for ti in order:
    print(f"  {TEAMS[ti]:<22} {pts_mean[ti]:6.1f} ± {pts_std[ti]:4.1f}   med={pts_med[ti]:3.0f}   [{pts_min[ti]:2d}–{pts_max[ti]:2d}]")
print()

# Expected GD
print("  EXPECTED GOAL DIFFERENCE (mean ± std)")
print("  " + "-" * 50)
gd_mean = all_gd.mean(axis=0)
gd_std = all_gd.std(axis=0)
order = np.argsort(gd_mean)[::-1]
for ti in order:
    sign = "+" if gd_mean[ti] >= 0 else ""
    print(f"  {TEAMS[ti]:<22} {sign}{gd_mean[ti]:5.1f} ± {gd_std[ti]:4.1f}")
print()

# Position distribution table
print("  POSITION DISTRIBUTION (% of 10,000 runs at each position)")
print("  " + "-" * 84)
print(f"  {'Team':<22} ", end="")
for pos in range(1, 21):
    print(f"{pos:>4}", end="")
print()
print(f"  {'─'*22} ", end="")
for pos in range(1, 21):
    print(f"{'─'*4}", end="")
print()

# Compute position distributions
for ti in range(N):
    # Sort each run to find this team's position
    positions = np.zeros(N_RUNS, dtype=int)
    for run_i in range(N_RUNS):
        order = np.lexsort((all_gd[run_i], all_points[run_i]))[::-1]
        pos = np.where(order == ti)[0][0] + 1
        positions[run_i] = pos

    print(f"  {TEAMS[ti]:<22} ", end="")
    for pos in range(1, 21):
        p = np.sum(positions == pos) / N_RUNS * 100
        if p >= 5:
            print(f"{p:3.0f}%", end="")
        elif p > 0:
            print(f"{p:3.1f}", end="")
        else:
            print(f"    ", end="")
    print()
print()

# Real vs Simulated
print("=" * 70)
print("  REAL 2024/25 vs SIMULATED EXPECTATION")
print("=" * 70)
print(f"  {'Team':<22} {'Real Pts':>8} {'Real Pos':>8} {'Sim Pts':>8} {'Sim Pos':>8} {'Δ Pts':>6}")
print(f"  {'─'*22} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")

REAL_PTS = [s[6] for s in SEASON]
REAL_POS = list(range(1, 21))

for ti in range(N):
    sim_p = pts_mean[ti]
    # Estimate simulated position
    sim_pos = 1
    for tj in range(N):
        if pts_mean[tj] > sim_p or (pts_mean[tj] == sim_p and gd_mean[tj] > gd_mean[ti]):
            sim_pos += 1
    delta = sim_p - REAL_PTS[ti]
    sign = "+" if delta >= 0 else ""
    print(f"  {TEAMS[ti]:<22} {REAL_PTS[ti]:>8} {REAL_POS[ti]:>8} {sim_p:>8.1f} {sim_pos:>8} {sign}{delta:>5.1f}")
print()

# Save
results = {
    "seed": SEED,
    "runs": N_RUNS,
    "model": "Poisson + Elo",
    "dataset": "Premier League 2024/25",
    "teams": TEAMS,
    "title_wins_pct": {TEAMS[i]: round(title_wins[i] / N_RUNS * 100, 2) for i in range(N)},
    "top4_pct": {TEAMS[i]: round(top4[i] / N_RUNS * 100, 2) for i in range(N)},
    "top6_pct": {TEAMS[i]: round(top6[i] / N_RUNS * 100, 2) for i in range(N)},
    "relegation_pct": {TEAMS[i]: round(relegation[i] / N_RUNS * 100, 2) for i in range(N)},
    "points_mean": {TEAMS[i]: round(float(pts_mean[i]), 1) for i in range(N)},
    "points_std": {TEAMS[i]: round(float(pts_std[i]), 1) for i in range(N)},
    "points_median": {TEAMS[i]: int(pts_med[i]) for i in range(N)},
    "gd_mean": {TEAMS[i]: round(float(gd_mean[i]), 1) for i in range(N)},
    "real_table": {
        TEAMS[i]: {"Pts": REAL_PTS[i], "Pos": REAL_POS[i],
                   "GF": SEASON[i][4], "GA": SEASON[i][5]}
        for i in range(N)
    },
}

with open("simulation_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"Results saved to simulation_results.json")
print(f"Seed: {SEED}  |  Runs: {N_RUNS:,}")
print("Done.")

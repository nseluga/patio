# Sport Bet-Generation Modules Analysis
## Item 3.1: Collapse 3 Sport Modules → 1 Parameterized Module

---

## Executive Summary

Three sport-specific bet-generation modules (`caps_bet_generation.py`, `pong_bet_generation.py`, `beerball_bet_generation.py`) share a common pipeline architecture with significant duplication and minor per-sport variations. This analysis maps the structure, differences, and parameterization opportunities to consolidate them into a single reusable module.

**Common Pipeline Flow** (all three sports):
1. **Fetch Players** → Get distinct player names from `player_stat_aggregates` filtered by game
2. **Build Profiles** → Query mean/std/mean_last_5 (and win_rate/defensive_value for some sports)
3. **Assemble Matchup** → Random team selection (identical logic across all three)
4. **Calculate Strength** → Normalize and composite player/team metrics
5. **Apply Opportunity Factor** → Adjust expected value based on balance/skill
6. **Apply House Bias** → Snap to half-point with percentile offset
7. **Return Line** → Final betting line

---

## 1. Top-Level Functions by Module

### CAPS Module (`caps_bet_generation.py`, 256 lines)

| Function | Signature | Purpose |
|----------|-----------|---------|
| `get_caps_shots_players` | `(cur, team_size)` → `list[str]` | Lines 9–19 |
| `get_player_caps_shots_profile` | `(cur, player_name, team_size)` → `dict` | Lines 21–35 |
| `get_caps_score_players` | `(cur, team_size)` → `list[str]` | Lines 37–46 |
| `get_player_caps_score_profile` | `(cur, player_name, team_size)` → `dict` | Lines 48–61 |
| `get_global_caps_score_strength_average` | `(cur, team_size, recency_weight=0.1)` → `float` | Lines 63–109 |
| `assemble_caps_matchup` | `(players, team_size)` → `dict` | Lines 111–134 |
| `opportunity_factor` | `(balance_ratio)` → `float` | Lines 136–156 |
| `harmonic_mean` | `(values)` → `float` | Lines 158–160 |
| `adjust` | `(stats, recency_weight)` → `float` | Lines 162–163 |
| `team_strength_multiplier` | `(strength, avg_strength)` → `float` | Lines 165–167 |
| `generate_biased_caps_shots_line` | `(subject_stats, teammates_stats, opp_team_stats, line_type, recency_weight=0.1)` → `float` | Lines 171–198 |
| `generate_biased_caps_score_line` | `(your_team_profiles, opp_team_profiles, your_team_shots, opp_team_shots, global_avg_strength, line_type, recency_weight=0.1)` → `(float, str)` | Lines 200–255 |

---

### PONG Module (`pong_bet_generation.py`, 250 lines)

| Function | Signature | Purpose |
|----------|-----------|---------|
| `get_pong_shots_players` | `(cur, team_size)` → `list[str]` | Lines 9–19 |
| `get_player_pong_shots_profile` | `(cur, player_name, team_size)` → `dict` | Lines 21–35 |
| `get_global_pong_shots_average` | `(cur, team_size)` → `float` | Lines 37–47 |
| `get_pong_score_players` | `(cur, team_size)` → `list[str]` | Lines 49–59 |
| `get_player_pong_score_profile` | `(cur, player_name, team_size)` → `dict` | Lines 61–75 |
| `get_global_pong_score_strength_average` | `(cur, team_size, recency_weight=0.1)` → `float` | Lines 77–113 |
| `assemble_pong_shots_matchup` | `(players, team_size)` → `dict` | Lines 115–138 |
| `adjust` | `(stats, recency_weight)` → `float` | Lines 140–141 |
| `team_advantage_factor` | `(balance_ratio)` → `float` | Lines 143–149 |
| `teammate_suppression_factor` | `(teammates_adj, global_avg)` → `float` | Lines 151–156 |
| `opportunity_factor` | `(balance_ratio, teammates_adj, global_avg)` → `float` | Lines 158–159 |
| `team_strength_multiplier` | `(strength, avg_strength)` → `float` | Lines 161–163 |
| `generate_biased_pong_shots_line` | `(subject_stats, teammates_stats, opp_team_stats, line_type, team_size, cur, recency_weight=0.1)` → `float` | Lines 165–196 |
| `generate_biased_pong_score_line` | `(your_team_profiles, opp_team_profiles, your_team_shots, opp_team_shots, global_avg_strength, line_type, recency_weight=0.1)` → `(float, str)` | Lines 198–249 |

---

### BEERBALL Module (`beerball_bet_generation.py`, 272 lines)

| Function | Signature | Purpose |
|----------|-----------|---------|
| `get_beerball_shots_players` | `(cur, team_size)` → `list[str]` | Lines 9–19 |
| `get_player_beerball_shots_profile` | `(cur, player_name, team_size)` → `dict` | Lines 21–35 |
| `get_beerball_score_players` | `(cur, team_size)` → `list[str]` | Lines 37–47 |
| `get_player_beerball_score_profile` | `(cur, player_name, team_size)` → `dict` | Lines 49–63 |
| `get_global_beerball_dv_average` | `(cur, team_size)` → `float` | Lines 65–76 |
| `get_global_beerball_score_strength_average` | `(cur, team_size, recency_weight=0.1)` → `float` | Lines 78–126 |
| `assemble_beerball_matchup` | `(players, team_size)` → `dict` | Lines 129–155 |
| `adjust` | `(stats, recency_weight)` → `float` | Lines 157–158 |
| `opportunity_factor` | `(your_win_rate, opp_win_rate, avg_opp_dv, avg_dv_center)` → `float` | Lines 160–176 |
| `team_strength_multiplier` | `(strength, avg_strength)` → `float` | Lines 178–180 |
| `generate_biased_beerball_shots_line` | `(cur, team_size, subject_stats, your_win_rate, opp_win_rate, avg_opp_dv, line_type, recency_weight=0.1)` → `float` | Lines 182–200 |
| `generate_biased_beerball_score_line` | `(your_team_profiles, opp_team_profiles, your_team_shots, opp_team_shots, global_avg_strength, line_type, recency_weight=0.1)` → `(float, str)` | Lines 202–271 |

---

## 2. Shared Pipeline Steps and Identical Logic

### 2.1 Pipeline Stage: Fetch Players

**Status: IDENTICAL LOGIC**

All three modules fetch distinct player names from `player_stat_aggregates` with identical WHERE clause structure.

**CAPS (lines 10–17):**
```sql
SELECT DISTINCT player_name
FROM player_stat_aggregates
WHERE game_played = 'Caps'
  AND game_type = 'Shots Made'
  AND stat_name = 'shots_made'
  AND team_size = %s
```

**PONG (lines 10–17):**
```sql
SELECT DISTINCT player_name
FROM player_stat_aggregates
WHERE game_played = 'Pong'
  AND game_type = 'Shots Made'
  AND stat_name = 'shots_made'
  AND team_size = %s
```

**BEERBALL (lines 10–17):**
```sql
SELECT DISTINCT player_name
FROM player_stat_aggregates
WHERE game_played = 'Beerball'
  AND game_type = 'Shots Made'
  AND stat_name = 'shots_made'
  AND team_size = %s
```

**Parameterization:** Replace string literal `'Caps'`/`'Pong'`/`'Beerball'` with parameter `game_name`.

---

### 2.2 Pipeline Stage: Get Player Profile

**Status: MOSTLY IDENTICAL**

All three fetch `mean`, `std`, `mean_last_5` (and optionally `win_rate`, `defensive_value`).

**CAPS (lines 22–30):**
```sql
SELECT mean, std, mean_last_5
FROM player_stat_aggregates
WHERE player_name = %s
  AND game_played = 'Caps'
  AND game_type = 'Shots Made'
  AND stat_name = 'shots_made'
  AND team_size = %s
```

**BEERBALL Score Profile (lines 50–58):**
```sql
SELECT mean, mean_last_5, win_rate, defensive_value
FROM player_stat_aggregates
WHERE player_name = %s
  AND game_played = 'Beerball'
  AND game_type = 'Score'
  AND stat_name = 'score'
  AND team_size = %s
```

**Differences:**
- CAPS/PONG: Select `std` (needed for normal distribution percentile)
- BEERBALL: Selects `defensive_value` for score profiles only
- CAPS: No `win_rate` in shots queries, but fetches in score queries
- BEERBALL: Always fetches `win_rate` and `defensive_value` from score profiles

---

### 2.3 Pipeline Stage: Assemble Matchup

**Status: IDENTICAL LOGIC** (all three modules)

All three implement identical team assembly, just naming differs.

**CAPS (lines 111–134):**
```python
def assemble_caps_matchup(players, team_size):
    assert len(players) >= 2 * team_size, "Not enough players for matchup"
    selected = random.sample(players, 2 * team_size)
    your_team = selected[:team_size]
    opp_team = selected[team_size:]
    playerA = your_team[0]  # line subject
    # ...build matchup string...
    return {
        "your_team": your_team,
        "opp_team": opp_team,
        "line_subject": playerA,
        "matchup": matchup
    }
```

**PONG (lines 115–138):** Identical logic, different name.  
**BEERBALL (lines 129–155):** Identical logic, different name.

**Parameterization:** Consolidate to single `assemble_matchup(players, team_size, game_name)`.

---

### 2.4 Pipeline Stage: Recency-Weighted Adjustment

**Status: IDENTICAL LOGIC** (all three modules)

All define `adjust(stats, recency_weight)` identically:

**All three (CAPS line 162–163, PONG line 140–141, BEERBALL line 157–158):**
```python
def adjust(stats, recency_weight):
    return stats["mean"] + (stats["mean_last_5"] - stats["mean"]) * recency_weight
```

**Parameterization:** Extract to shared utility function.

---

### 2.5 Pipeline Stage: Team Strength Multiplier

**Status: IDENTICAL LOGIC** (all three modules)

All three define `team_strength_multiplier(strength, avg_strength)` identically:

**CAPS (lines 165–167):**
```python
def team_strength_multiplier(strength, avg_strength):
    deviation = strength - avg_strength
    return 1.0 + max(min(deviation * 0.75, 0.3), -0.3)
```

**PONG (lines 161–163):** Identical.  
**BEERBALL (lines 178–180):** Identical.

**Parameterization:** Extract to shared utility function.

---

### 2.6 Pipeline Stage: House Bias (Percentile & Half-Point Snap)

**Status: IDENTICAL LOGIC** (all three modules)

All three apply the same bias mechanism:

**CAPS Shots (lines 189–194):**
```python
percentile = 0.47 if line_type == "Over" else 0.53
subj_std = subject_stats["std"]
line = norm(expected, subj_std).ppf(percentile)
base = round(line)
final_line = base - 0.5 if line_type == "Over" else base + 0.5
```

**PONG Shots (lines 184–191):**
```python
percentile = 0.48 if line_type == "Over" else 0.52  # SLIGHT DIFF
subj_std = subject_stats["std"]
line = norm(expected, subj_std).ppf(percentile)
base = round(line)
if line_type == "Over":
    final_line = min(base - 0.5, 9.5)  # Capped at 9.5
else:
    final_line = min(base + 0.5, 9.5)
```

**BEERBALL Shots (lines 190–195):**
```python
percentile = 0.47 if line_type == "Over" else 0.53  # Same as CAPS
subj_std = subject_stats["std"]
line = norm(expected, subj_std).ppf(percentile)
base = round(line)
final_line = base - 0.5 if line_type == "Over" else base + 0.5
```

**Variations:**
- PONG shots: `percentile = 0.48/0.52` (vs 0.47/0.53 for CAPS/BEERBALL)
- PONG shots: Capped at 9.5 (sport-specific max line)

**Score Lines (all three, lines ~244–246):**
```python
percentile = 0.47 if line_type == "Over" else 0.53
line = norm(expected_margin, std=1.5).ppf(percentile)
if line < 0:
    line = abs(line)
    line_type = "Under"
base = round(line)
final_line = base - 0.5 if line_type == "Over" else base + 0.5
```

**Parameterization:** Extract percentile and line cap as sport parameters.

---

## 3. Per-Sport-Specific Logic (Differences)

### 3.1 Opportunity Factor

**CAPS (lines 136–156):** Balance-ratio-only model
```python
def opportunity_factor(balance_ratio):
    deviation = abs(balance_ratio - 1.0)
    if deviation < 0.05:
        return 1.4
    elif balance_ratio > 1.0:
        if deviation < 0.15: return 1.3
        elif deviation < 0.35: return 1.1
        else: return 0.9
    else:  # balance_ratio < 1.0
        if deviation < 0.15: return 1.1
        elif deviation < 0.35: return 0.9
        else: return 0.7
```

**PONG (lines 158–159):** Two-factor model
```python
def opportunity_factor(balance_ratio, teammates_adj, global_avg):
    return team_advantage_factor(balance_ratio) * teammate_suppression_factor(teammates_adj, global_avg)

def team_advantage_factor(balance_ratio):
    balance_ratio = max(0.4, min(balance_ratio, 2.5))  # Clamp
    exponent = 0.5  # √ratio for smoothing
    return balance_ratio ** exponent

def teammate_suppression_factor(teammates_adj, global_avg):
    avg_teammate_score = sum(teammates_adj) / len(teammates_adj) if teammates_adj else 0
    diff = avg_teammate_score - global_avg
    suppression = 1.0 - 0.04 * diff  # Steep scaling
    return max(0.8, min(suppression, 1.1))  # Clamp
```

**BEERBALL (lines 160–176):** Win-rate + defensive-value model
```python
def opportunity_factor(your_win_rate, opp_win_rate, avg_opp_dv, avg_dv_center):
    skill_ratio = your_win_rate / opp_win_rate if opp_win_rate > 0 else 1.0
    if skill_ratio >= 1:
        skill_bonus = min(1.0 + 0.4 * (skill_ratio - 1.0), 1.4)
    else:
        skill_bonus = max(1.0 - 0.6 * (1.0 - skill_ratio), 0.7)
    
    def defensive_adjustment(dv, center):
        steepness = np.log(81) / 0.45  # ~5.5
        scale = 0.7
        max_boost = 1.4
        return scale + (max_boost - scale) * (1 / (1 + np.exp(steepness * (center - dv))))
    
    defense_penalty = defensive_adjustment(avg_opp_dv, avg_dv_center)
    return skill_bonus * defense_penalty
```

**Key Differences:**
- CAPS: Simple balance-ratio thresholds
- PONG: Balance ratio × teammate suppression (accounts for strong/weak teammates)
- BEERBALL: Skill ratio (win_rate) × defensive value (sigmoid curve for DV adjustment)

---

### 3.2 Expected Stat Calculation (predict_expected_stat)

**CAPS Shots (lines 176–186):**
```python
your_team_vals = [subj_adj] + team_adj
team_strength = harmonic_mean(your_team_vals)
opp_strength = harmonic_mean(opp_adj)
balance_ratio = team_strength / opp_strength if opp_strength > 0 else 1
opportunity = opportunity_factor(balance_ratio)
expected = subj_adj * opportunity
```

**PONG Shots (lines 166–180):**
```python
your_team_vals = [subj_adj] + team_adj
opp_team_vals = opp_adj
team_strength = sum(your_team_vals) / len(your_team_vals)  # ARITHMETIC MEAN
opp_strength = sum(opp_team_vals) / len(opp_team_vals)
global_avg = get_global_pong_shots_average(cur, team_size)
balance_ratio = team_strength / opp_strength if opp_strength > 0 else 1.0
opportunity = opportunity_factor(balance_ratio, team_adj, global_avg)
expected = subj_adj * opportunity
```

**BEERBALL Shots (lines 182–188):**
```python
subj_adj = adjust(subject_stats, recency_weight)
avg_dv = get_global_beerball_dv_average(cur, team_size)
opportunity = opportunity_factor(your_win_rate, opp_win_rate, avg_opp_dv, avg_dv)
expected = subj_adj * opportunity
```

**Key Differences:**
- CAPS: Harmonic mean (emphasizes weakest player)
- PONG: Arithmetic mean (standard average) + teammate suppression
- BEERBALL: Only uses subject stats + win_rate/DV, no team composition in shots

---

### 3.3 Score Line Composition (player_strength weighting)

**CAPS Score (lines 208–220):**
```python
w1, w2, w3 = 0.25, 0.25, 0.25  # Score, Shots, Win_rate (3 weights)

def player_strength(profile, shots):
    adj_score = adjust(profile, recency_weight)
    win_rate = profile.get("win_rate", 0.5)
    norm_score = adj_score / 8          # Normalize score by 8
    norm_shots = shots / 16             # Normalize shots by 16
    return (
        w1 * norm_score +
        w2 * norm_shots +
        w3 * win_rate
    )
```

**PONG Score (lines 208–217):**
```python
w1, w2, w3 = 0.25, 0.25, 0.25  # 3 weights (same)

def player_strength(profile, shots):
    adj_score = adjust(profile, recency_weight)
    win_rate = profile.get("win_rate", 0.5)
    norm_score = adj_score / 10         # Normalize score by 10 (DIFFERENT)
    norm_shots = shots / 10             # Normalize shots by 10 (DIFFERENT)
    return (
        w1 * norm_score +
        w2 * norm_shots +
        w3 * win_rate
    )
```

**BEERBALL Score (lines 210–222):**
```python
w1, w2, w3, w4 = 0.25, 0.25, 0.25, 0.25  # 4 weights (includes DV)

def player_strength(profile, shots_made):
    adj_score = adjust(profile, recency_weight)
    win_rate = profile.get("win_rate", 0.5)
    dv = profile.get("defensive_value", 0.5)
    norm_score = adj_score / 3          # Normalize score by 3 (LOWER)
    norm_shots = shots_made / 10        # Normalize shots by 10
    return (
        w1 * norm_score +
        w2 * norm_shots +
        w3 * win_rate +
        w4 * dv                         # DEFENSIVE VALUE
    )
```

**Key Differences:**
- CAPS: 3 components, score norm = 8, shots norm = 16
- PONG: 3 components, score norm = 10, shots norm = 10
- BEERBALL: 4 components (adds defensive_value), score norm = 3, shots norm = 10

---

### 3.4 Global Strength Average Calculation

**CAPS (lines 63–109):**
- Fetches player score + win_rate
- Fetches shots made separately
- Strength = 0.25 × score_adj + 0.25 × shots + 0.25 × win_rate (+ implicit 0.25 padding)
- Uses `harmonic_mean()` helper

**PONG (lines 77–113):**
- Fetches player score + win_rate
- Fetches shots made separately
- Strength = 0.25 × (score_adj / 10) + 0.25 × (shots / 10) + 0.25 × win_rate
- Uses `np.mean()` directly

**BEERBALL (lines 78–126):**
- Fetches player score + win_rate + defensive_value
- Fetches shots made separately
- Strength = 0.25 × adjust + 0.25 × shots + 0.25 × win_rate + 0.25 × defensive_value
- Returns `np.mean(strengths)`

---

## 4. Database Queries by Module

### 4.1 CAPS Module Queries

| Query Name | Location | SQL | Purpose |
|-----------|----------|-----|---------|
| Get Shots Players | 10–17 | `SELECT DISTINCT player_name FROM player_stat_aggregates WHERE game_played='Caps' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Fetch all Caps shots players |
| Get Shots Profile | 22–30 | `SELECT mean, std, mean_last_5 FROM player_stat_aggregates WHERE player_name=%s AND game_played='Caps' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Get single player shots stats |
| Get Score Players | 38–45 | `SELECT DISTINCT player_name FROM player_stat_aggregates WHERE game_played='Caps' AND game_type='Score' AND stat_name='score' AND team_size=%s` | Fetch all Caps score players |
| Get Score Profile | 49–57 | `SELECT mean, std, mean_last_5 FROM player_stat_aggregates WHERE player_name=%s AND game_played='Caps' AND game_type='Score' AND stat_name='score' AND team_size=%s` | Get single player score stats |
| Get Global Strength | 64–71 | `SELECT player_name, mean, mean_last_5, win_rate FROM player_stat_aggregates WHERE game_played='Caps' AND game_type='Score' AND stat_name='score' AND team_size=%s` | Fetch all score profiles + win_rate |
| Get Shots for Strength | 75–83 | `SELECT player_name, mean FROM player_stat_aggregates WHERE player_name = ANY(%s) AND game_played='Caps' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Cross-join shots for strength calc |

---

### 4.2 PONG Module Queries

| Query Name | Location | SQL | Purpose |
|-----------|----------|-----|---------|
| Get Shots Players | 10–17 | `SELECT DISTINCT player_name FROM player_stat_aggregates WHERE game_played='Pong' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Fetch all Pong shots players |
| Get Shots Profile | 22–30 | `SELECT mean, std, mean_last_5 FROM player_stat_aggregates WHERE player_name=%s AND game_played='Pong' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Get single player shots stats |
| Get Shots Average | 38–45 | `SELECT AVG(mean) AS avg_mean FROM player_stat_aggregates WHERE game_played='Pong' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Global avg shots (fallback 4.0) |
| Get Score Players | 50–57 | `SELECT DISTINCT player_name FROM player_stat_aggregates WHERE game_played='Pong' AND game_type='Score' AND stat_name='score' AND team_size=%s` | Fetch all Pong score players |
| Get Score Profile | 62–70 | `SELECT mean, std, mean_last_5, win_rate FROM player_stat_aggregates WHERE player_name=%s AND game_played='Pong' AND game_type='Score' AND stat_name='score' AND team_size=%s` | Get single player score stats (includes std) |
| Get Global Strength | 78–85 | `SELECT player_name, mean, mean_last_5, win_rate FROM player_stat_aggregates WHERE game_played='Pong' AND game_type='Score' AND stat_name='score' AND team_size=%s` | Fetch all score profiles + win_rate |
| Get Shots for Strength | 90–94 | `SELECT player_name, mean FROM player_stat_aggregates WHERE player_name = ANY(%s) AND game_played='Pong' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Cross-join shots for strength calc |

---

### 4.3 BEERBALL Module Queries

| Query Name | Location | SQL | Purpose |
|-----------|----------|-----|---------|
| Get Shots Players | 10–17 | `SELECT DISTINCT player_name FROM player_stat_aggregates WHERE game_played='Beerball' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Fetch all Beerball shots players |
| Get Shots Profile | 22–30 | `SELECT mean, std, mean_last_5 FROM player_stat_aggregates WHERE player_name=%s AND game_played='Beerball' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Get single player shots stats |
| Get Score Players | 38–46 | `SELECT DISTINCT player_name FROM player_stat_aggregates WHERE game_played='Beerball' AND game_type='Score' AND stat_name='score' AND team_size=%s` | Fetch all Beerball score players |
| Get Score Profile | 50–58 | `SELECT mean, mean_last_5, win_rate, defensive_value FROM player_stat_aggregates WHERE player_name=%s AND game_played='Beerball' AND game_type='Score' AND stat_name='score' AND team_size=%s` | Get single player score stats (NO std, includes DV) |
| Get DV Average | 66–74 | `SELECT AVG(defensive_value) AS avg_dv FROM player_stat_aggregates WHERE game_played='Beerball' AND game_type='Score' AND stat_name='score' AND team_size=%s AND defensive_value IS NOT NULL` | Global avg DV (fallback 0.7) |
| Get Global Strength | 79–86 | `SELECT player_name, mean, mean_last_5, win_rate, defensive_value FROM player_stat_aggregates WHERE game_played='Beerball' AND game_type='Score' AND stat_name='score' AND team_size=%s` | Fetch all score profiles (includes DV) |
| Get Shots for Strength | 90–98 | `SELECT player_name, mean FROM player_stat_aggregates WHERE player_name = ANY(%s) AND game_played='Beerball' AND game_type='Shots Made' AND stat_name='shots_made' AND team_size=%s` | Cross-join shots for strength calc |

---

## 5. `get_or_create_bettable_player` Usage

### Current Usage Pattern

Located in `/Users/nateseluga/Downloads/Patio/backend/stats_utils.py` (lines 224–234):

```python
def get_or_create_bettable_player(cur, name):
    cur.execute("SELECT id FROM bettable_players WHERE LOWER(name) = LOWER(%s)", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    
    cur.execute(
        "INSERT INTO bettable_players (name) VALUES (%s) RETURNING id",
        (name,)
    )
    return cur.fetchone()["id"]
```

### Actual Usage in Bet Generation Modules

**NONE OF THE THREE BET-GENERATION MODULES USE THIS FUNCTION.**

- The three bet generation modules (`caps_bet_generation.py`, `pong_bet_generation.py`, `beerball_bet_generation.py`) only **read** from `player_stat_aggregates`
- They never create or retrieve player records from `bettable_players`
- This function is used only in:
  - `stats_utils.py` internal flow (line 121, for DV calculation in `update_player_aggregate`)
  - `routes/submit_routes.py` (lines ~150, 200, 250 — when bet results are submitted)

**Implication for Consolidation:**
- The parameterized module won't need `get_or_create_bettable_player` unless the architecture changes to allow on-the-fly player creation during bet generation
- Currently, player records must exist in both `bettable_players` and `player_stat_aggregates` before a bet can be generated

---

## 6. Opportunity Factor & House Bias Logic

### 6.1 House Bias (Percentile & Half-Point Snap)

**Status: NEARLY IDENTICAL** with three variations:

**CAPS & BEERBALL Shots:**
- Percentile: 0.47 (Over) / 0.53 (Under)
- Snap: ±0.5 based on line_type
- No cap

**PONG Shots:**
- Percentile: 0.48 (Over) / 0.52 (Under) — **SLIGHTLY DIFFERENT**
- Snap: ±0.5 based on line_type
- **Capped at 9.5** (sport-specific maximum)

**All Score Lines:**
- Percentile: 0.47 (Over) / 0.53 (Under)
- Snap: ±0.5 based on line_type
- Negative line flip: If line < 0, use abs(line) and swap Over/Under

**Parameterization:** Create `line_bias_config` dict per sport:
```python
{
    'caps': {'percentile_over': 0.47, 'percentile_under': 0.53, 'line_cap': None},
    'pong': {'percentile_over': 0.48, 'percentile_under': 0.52, 'line_cap': 9.5},
    'beerball': {'percentile_over': 0.47, 'percentile_under': 0.53, 'line_cap': None}
}
```

---

### 6.2 Opportunity Factor

| Sport | Formula | Inputs | Range | Notes |
|-------|---------|--------|-------|-------|
| CAPS | Discrete thresholds on balance_ratio | balance_ratio | 0.7–1.4 | 7 discrete branches; if balanced ±5% → max 1.4 |
| PONG | team_advantage_factor × teammate_suppression | balance_ratio, teammate_adj, global_avg | ~0.63–1.5 (combined) | Clamped balance_ratio [0.4, 2.5]; suppression [0.8, 1.1] |
| BEERBALL | skill_bonus × defensive_adjustment | your_win_rate, opp_win_rate, avg_opp_dv, avg_dv_center | ~0.7–1.4 × 0.7–1.4 | Sigmoid DV curve; win_rate ratios |

---

## 7. Sport-Specific Constants & Thresholds

### Score Normalization Factors

| Sport | Score Norm | Shots Norm | Reasoning |
|-------|-----------|-----------|-----------|
| CAPS | 8 | 16 | Assumes max score ~8, max shots ~16 |
| PONG | 10 | 10 | Assumes both on 0–10 scale (or ~10 expected) |
| BEERBALL | 3 | 10 | Beerball scores lower (~3 expected), shots ~10 |

### Line Biasing (Percentile)

| Bet Type | CAPS | PONG | BEERBALL |
|----------|------|------|----------|
| Shots Over | 0.47 | 0.48 | 0.47 |
| Shots Under | 0.53 | 0.52 | 0.53 |
| Score Over | 0.47 | 0.47 | 0.47 |
| Score Under | 0.53 | 0.53 | 0.53 |

### Line Caps

| Sport | Shots Cap | Score Cap | Notes |
|-------|----------|-----------|-------|
| CAPS | None | None | Unconstrained |
| PONG | 9.5 | None | Shots capped at 9.5; score uncapped |
| BEERBALL | None | None | Unconstrained |

### Global Defaults (Fallback Values)

| Lookup | CAPS | PONG | BEERBALL |
|--------|------|------|----------|
| Avg Shots (if no data) | — | 4.0 | — |
| Avg DV (if no data) | — | — | 0.7 |

---

## 8. DB Column Usage: mean, win_rate, defensive_value, mean_last_5

### By Query Type & Sport

**Shots Profile Queries:**

| Sport | Columns Selected | win_rate | defensive_value | std |
|-------|-----------------|----------|-----------------|-----|
| CAPS | mean, std, mean_last_5 | ✗ | ✗ | ✓ |
| PONG | mean, std, mean_last_5 | ✗ | ✗ | ✓ |
| BEERBALL | mean, std, mean_last_5 | ✗ | ✗ | ✓ |

**Score Profile Queries:**

| Sport | Columns Selected | win_rate | defensive_value | std |
|-------|-----------------|----------|-----------------|-----|
| CAPS | mean, std, mean_last_5 | ✗ | ✗ | ✓ |
| PONG | mean, std, mean_last_5, win_rate | ✓ | ✗ | ✓ |
| BEERBALL | mean, mean_last_5, win_rate, defensive_value | ✓ | ✓ | ✗ |

**Global Strength Queries:**

| Sport | win_rate Behavior | defensive_value Behavior | mean_last_5 Behavior |
|-------|-------------------|--------------------------|----------------------|
| CAPS | Fetched in strength avg; fallback 0.5 | — | Used in `adjust()` with weight 0.1 |
| PONG | Fetched in strength avg; fallback 0.5 | — | Used in `adjust()` with weight 0.1 |
| BEERBALL | Fetched in strength avg; fallback 0.5 | Fetched in strength avg; fallback 0.5 | Used in `adjust()` with weight 0.1 |

**Key Pattern:** All three modules use `adjust(stats, recency_weight=0.1)` to blend `mean` with `mean_last_5` at 10% recency weight. If `mean_last_5` is missing, they silently treat it as 0, which produces `mean + (0 - mean) × 0.1 = 0.9 × mean` — **potential bug if mean_last_5 is NULL**.

---

## 9. Summary Table: Parameterization Candidates

| Component | CAPS | PONG | BEERBALL | Consolidation Strategy |
|-----------|------|------|----------|------------------------|
| **Game Name** | 'Caps' | 'Pong' | 'Beerball' | Param: `game_name` |
| **Fetch Players** | Identical | Identical | Identical | Single function with `game_name` |
| **Get Profile (Shots)** | mean, std, mean_last_5 | mean, std, mean_last_5 | mean, std, mean_last_5 | Single function; std always needed |
| **Get Profile (Score)** | mean, std, mean_last_5 | mean, std, mean_last_5, win_rate | mean, mean_last_5, win_rate, defensive_value | Conditional: select std/dv per sport |
| **Assemble Matchup** | Identical | Identical | Identical | Single function; differ only in naming |
| **adjust()** | Identical | Identical | Identical | Extract to shared utils |
| **team_strength_multiplier()** | Identical | Identical | Identical | Extract to shared utils |
| **opportunity_factor()** | ✓ Balance-ratio | ✓ Balance + teammates | ✓ Win-rate + DV | Sport-specific function pointers |
| **Expected Stat Calc** | Harmonic mean | Arithmetic mean | Direct (no team) | Sport-specific function pointers |
| **Score Strength Calc** | norm/8, shots/16, wr | norm/10, shots/10, wr | norm/3, shots/10, wr, dv | Sport-specific multipliers + weights |
| **Line Bias Percentile** | 0.47/0.53 | 0.48/0.52 | 0.47/0.53 | Sport param dict |
| **Line Cap** | None | 9.5 (shots) | None | Sport param dict |
| **Global Avg Fallback** | — | shots: 4.0 | dv: 0.7 | Sport param dict |

---

## 10. Recommended Parameterized Module Structure

```python
# consolidated_bet_generation.py

SPORT_CONFIG = {
    'caps': {
        'game_name': 'Caps',
        'percentile_over': 0.47,
        'percentile_under': 0.53,
        'shots_cap': None,
        'score_norm': 8,
        'shots_norm': 16,
        'strength_weights': (0.25, 0.25, 0.25),  # score, shots, win_rate
        'strength_use_dv': False,
        'avg_shots_fallback': None,
        'avg_dv_fallback': None,
        'team_aggregation': 'harmonic_mean',  # for shots expected value
    },
    'pong': {
        'game_name': 'Pong',
        'percentile_over': 0.48,
        'percentile_under': 0.52,
        'shots_cap': 9.5,
        'score_norm': 10,
        'shots_norm': 10,
        'strength_weights': (0.25, 0.25, 0.25),
        'strength_use_dv': False,
        'avg_shots_fallback': 4.0,
        'avg_dv_fallback': None,
        'team_aggregation': 'arithmetic_mean',  # for shots expected value
    },
    'beerball': {
        'game_name': 'Beerball',
        'percentile_over': 0.47,
        'percentile_under': 0.53,
        'shots_cap': None,
        'score_norm': 3,
        'shots_norm': 10,
        'strength_weights': (0.25, 0.25, 0.25, 0.25),  # score, shots, win_rate, dv
        'strength_use_dv': True,
        'avg_shots_fallback': None,
        'avg_dv_fallback': 0.7,
        'team_aggregation': None,  # N/A for shots (no team in expected)
    },
}

# Core parameterized functions:
def get_sport_players(cur, sport, game_type, team_size)
def get_player_profile(cur, player_name, sport, game_type, team_size)
def assemble_matchup(players, team_size)
def adjust(stats, recency_weight=0.1)
def team_strength_multiplier(strength, avg_strength)

# Sport-specific (via strategy pattern or dispatch):
def get_opportunity_factor(sport, **kwargs)  # delegates to sport-specific impl
def calculate_expected_stat(sport, **kwargs)  # delegates to sport-specific impl
def calculate_player_strength(sport, profile, shots, recency_weight=0.1)  # delegates

# Consolidated line generation:
def generate_biased_line(
    sport, line_type, game_type, expected_value, subject_stats,
    cur=None, team_size=None, additional_params=None
)
```

---

## File Locations & Line Ranges

| File | Module | Lines | Key Functions |
|------|--------|-------|----------------|
| `/Users/nateseluga/Downloads/Patio/backend/caps_bet_generation.py` | CAPS | 1–256 | `generate_biased_caps_shots_line` (171–198), `generate_biased_caps_score_line` (200–255) |
| `/Users/nateseluga/Downloads/Patio/backend/pong_bet_generation.py` | PONG | 1–250 | `generate_biased_pong_shots_line` (165–196), `generate_biased_pong_score_line` (198–249) |
| `/Users/nateseluga/Downloads/Patio/backend/beerball_bet_generation.py` | BEERBALL | 1–272 | `generate_biased_beerball_shots_line` (182–200), `generate_biased_beerball_score_line` (202–271) |
| `/Users/nateseluga/Downloads/Patio/backend/stats_utils.py` | Shared | 1–235 | `get_or_create_bettable_player` (224–234), `update_player_aggregate` (59–222) |
| `/Users/nateseluga/Downloads/Patio/backend/routes/lines_routes.py` | Router | 1–589 | Calls to all 6 line-generation functions (shots & score for each sport) |

---

## Conclusion

**Consolidation Feasibility: HIGH**

All three modules follow the same pipeline with:
- 60–70% identical code (fetch, assemble, adjust, team_strength_multiplier, house bias snap)
- 20–30% easily parameterized differences (score/shots norms, percentiles, line caps, fallback values)
- 10–15% sport-specific algorithms (opportunity_factor, expected_stat aggregation, player_strength weighting)

**Recommended Approach:**
1. Extract shared utilities (`adjust`, `team_strength_multiplier`, common queries)
2. Create `SPORT_CONFIG` dict with all normalization/bias constants
3. Implement strategy functions for sport-specific logic (`opportunity_factor`, `calculate_expected_stat`)
4. Consolidate line-generation entry points to single parameterized function
5. Update `lines_routes.py` to call consolidated module with sport parameter

This will reduce LOC by ~40% (from ~780 LOC across three files to ~470 LOC in one file) while improving maintainability.


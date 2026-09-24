# Persistent Score Database — Technical Document

## 1. Feature Description

Right now the app forgets everything the moment it closes — high scores live only in memory and reset on every restart, and there's no concept of who is even playing. This feature adds a permanent record of every player and every round ever played. When the app opens, the player picks their name from a list of everyone who's played before, or creates a new name if they're new. Their all-time best score is shown immediately, pulled from that saved history. Every time a round ends — whether the bird dies or the player just quits mid-game — that round's score gets saved permanently, tagged with the player's name and the date and time it happened. If that score beats their previous best, their all-time high score updates. The player can play as many rounds as they want in one sitting, and everything is still there the next time the app is opened, days or weeks later.

## 2. Technical Solution (Plain-Language Overview)

1. Add a small local file that acts like a permanent notebook, remembering every player's name, their best score, and a log of every round they've ever played.
2. When the app starts, read that notebook and show a list of everyone who's played before, so the player can pick their name — or write in a brand-new name if they're new.
3. As soon as a name is picked or created, look up (or start) that player's best score and show it on screen.
4. Let the player start playing as normal, with one small addition: their current all-time best score is shown alongside the live score during play, so they have something to beat in real time.
5. The game itself never talks to the notebook. It just keeps a running list of every round played in that sitting, each entry noting both the score and the moment that round ended — a new entry is added to the list each time a round ends, whether the bird dies (and the player keeps going again in the same sitting) or the player closes the game window mid-round.
6. The instant the game window closes, that whole list is handed back and written down permanently, one round at a time: who played, when, and what score they got — with each write saved to disk immediately, so a crash right after mid-session play never loses more than what hasn't been handed back yet.
7. After each round is written down, check if that score beats the player's previous best. If it does, update their best score in the notebook.
8. Update what's shown on screen to reflect the (possibly new) best score, straight from the notebook rather than from anything remembered in-app.
9. Keep the notebook file itself separate from the project's source code, since it holds personal player data, not program logic.

## 3. Alternatives and Design Decisions Strayed Away From

- **Storing a player's best score and round-count directly on every saved round, instead of calculating them when needed.** This was considered because it seemed like it would make each saved round "self-contained." It was dropped because it creates two sources of truth that can drift apart — if the best score is ever recalculated differently later, every old saved round would still show the outdated number. Calculating those values on the fly instead means there is only ever one true record.
- **Matching player names loosely** (ignoring capitalization/spacing so "Alex" and "alex" count as the same person). This was dropped in favor of a strict, exact-match name list that the player picks from rather than retypes — since the player never has to retype an existing name, the risk of accidentally creating a duplicate profile through a typo disappears on its own, without needing extra cleanup rules.
- **Using a full networked database system** instead of a single local file. This would only make sense if multiple computers needed to share the same player data over a network, which isn't the case here — this is a single-computer, single-player-at-a-time app, so a full server would add setup complexity with no real benefit.
- **Storing the notebook file in a special system folder** outside the project (the way some apps hide their data in system-level folders) instead of right next to the project files. This was considered for tidiness, but it makes the file harder to find and adds extra platform-specific handling. Keeping it next to the project (while excluding it from version control) was simpler and good enough for this app's scale.
- **Reopening a fresh connection to the notebook every single time something needs to be read or written**, instead of keeping one connection open for as long as the app runs. Both approaches work safely here, but keeping one connection open avoids repeatedly opening and closing the file for no benefit.
- **Only recording a round if the player actually died**, ignoring rounds where the player just quits partway through. This was dropped because it would silently lose data — quitting mid-round is still a real attempt and was decided to be worth keeping, even if it occasionally logs a very short, low-score round.
- **Letting the player switch names without restarting the app, and/or adding a leaderboard screen showing everyone's scores.** Both were discussed as natural next steps but intentionally left out of this version to keep the first implementation focused; the way the data is being stored doesn't block adding either one later.
- **Handing the game a live connection to the notebook so it can log each round itself as it happens**, instead of having the game simply track scores in memory and hand back the full list once the window closes. This was dropped because it would require the game to also track whether a just-finished round had already been logged (to avoid double-logging the same round if the window closes right after a death) — extra bookkeeping made unnecessary by having the game just report what happened and letting the launcher screen do the actual writing.
- **Batching round-writes and only committing them to disk when the app exits cleanly**, instead of committing each round the instant it's written. This was dropped because a crash or force-quit between commits would silently lose every round played since the last one — defeating the entire point of a permanent record.
- **Allowing any typed name to be saved as-is**, including blank or whitespace-only names. This was dropped in favor of trimming whitespace and rejecting empty names at creation time, so accidental blank profiles aren't created; this is separate from (and doesn't attempt to solve) the broader question of near-duplicate names like "Alex" vs. "alex", which remains a known limitation (see Section 5).

## 4. Detailed Step-by-Step Implementation Plan

### Step 1 — Create a new file: `scores_db.py`
This new file becomes the single place in the whole project that talks to the notebook file directly. Nothing else in the project will read or write player data except through this file. The notebook is a single SQLite database file (using Python's built-in `sqlite3` module), named `scores.db`, stored at the project root.
- Add a function that opens (or creates, if it doesn't exist yet) the `scores.db` file and sets up its two record-keeping sections the first time it's ever run: one section for player profiles (name + all-time best score), one section for individual rounds played (which player, when, what score). This function returns the open connection, and every other function in this file below takes that same connection as its first argument — nothing here opens its own separate connection.
- Add a function that returns the full list of player names that already exist, sorted alphabetically.
- Add a function that, given a name, either finds that player's existing profile or creates a brand-new one if the name has never been used, and returns their current best score either way — a brand-new profile starts with a best score of `0`. The player's name (already trimmed by the caller) is used as-is as their identifier for every other function in this file; no separate numeric ID is exchanged with the rest of the app.
- Add a function that, given a player, a score, and when that round happened, permanently logs that round and updates the player's best score if the new score is *strictly greater than* the current best (a tie does not update it) — done as a single combined step so the two things can never fall out of sync with each other, and committed to disk immediately as part of that same step so a crash right after never leaves the log and the best score disagreeing.
- Every query in this file is parameterized (no manually building query strings out of player-typed input), since player names come straight from free-typed user input.

### Step 2 — Modify `.gitignore`
- Add an entry excluding `scores.db` from version control, so player names and scores are never pushed to GitHub alongside the project's source code.

### Step 3 — Modify `flappy_app.py` (the launcher screen)
- On startup, open the notebook file once (using the function from Step 1) and keep that connection open for as long as the app is running.
- Replace the static "Play" screen with one that shows the list of existing player names (from Step 1) in a selectable list, plus a way to type in a new name. Typed names are trimmed of leading/trailing whitespace, and a blank (empty or whitespace-only) name is rejected — the name field or Play button simply won't accept it, no error dialog needed.
- When a name is picked or newly created, look up that player's current best score and display it immediately.
- Keep the Play button disabled until a valid (non-blank) name has been picked or created.
- When Play is clicked, hand off to the game screen along with which player is currently selected and their current best score (just the number, for on-screen display — the game itself never touches the notebook).
- When control returns from the game screen, it hands back a list of every round played in that sitting, each as a (score, when-it-ended) pair (see Step 4). Log each of those rounds, in order, via the Step 1 function, passing along that round's own recorded time rather than the current time — so rounds played minutes or hours apart in one long sitting still get their own distinct, accurate timestamps instead of all being stamped with whatever time logging happened to run. Once all of them are logged, re-read that player's best score fresh from the notebook and update what's shown on screen — rather than trusting any number the app might have remembered from before the round was played.
- Remove the old in-memory `self.high_score` tracking on `MainWindow` entirely — the notebook is now the only source of truth for best scores, so keeping a second in-memory copy would just risk it drifting out of sync.

### Step 4 — Modify `flappy_game.py` (the actual gameplay)
- Update the game's starting point so it also receives which player is currently playing (just for passing back with the results) and their current best score (a plain number, purely for display — no notebook access happens here).
- Show that best score on screen alongside the live score throughout play, so the player can see what they're trying to beat.
- Keep a simple in-memory list of (score, when-it-ended) pairs for the sitting, capturing the current moment (via Python's standard-library `datetime`, not the notebook) at the instant each round ends — this is purely local bookkeeping in the game process, not a write to the notebook. The moment a round ends because the bird died, append (current score, current time) to that list — the game already supports playing again immediately (press SPACE to restart) without closing the window, so this can happen more than once per sitting.
- If the player closes the game window while a round is still in progress (state is still "playing," not "game over"), append that in-progress round's (score, time) too before returning, so a quit mid-round is still counted as an attempt.
- If the player closes the game window right after a death (state is already "game over," meaning that round's (score, time) pair was already appended), don't append it again — checking the current game state is enough to avoid a duplicate entry; no separate marker/flag is needed.
- When the window closes, return the full list of (score, time) pairs collected during the sitting (instead of a single number) so `flappy_app.py` can log every one of them with its own accurate timestamp.
- Leave everything else about how the game is played untouched — physics, controls, obstacles, and visuals are unaffected by this feature. `flappy_game.py` still never imports or touches the notebook file directly.

### Step 5 — Manual verification pass
- Start the app for the very first time (no notebook file exists yet) and confirm it starts up cleanly with an empty player list.
- Confirm typing a blank or whitespace-only name does not let you create a profile, and that a name with extra leading/trailing spaces is trimmed before being saved.
- Create a new player, confirm they appear in the list with a starting best score, play a round to the end, and confirm the best score updates correctly if beaten. Confirm the in-game screen shows that best score alongside the live score while playing.
- Die, then press SPACE to play again several times without closing the window, then close the window — confirm every one of those rounds shows up as a separate entry once the app finishes logging them.
- Close the game window mid-round without dying, and confirm that round still gets logged.
- Die, then immediately close the window without restarting, and confirm that round was only logged once, not twice.
- Restart the app entirely and confirm the player list and best scores from the previous run are still there.
- Confirm the notebook file itself never shows up as a trackable change in version control.

## 5. Known Limitations

These were identified as gaps but intentionally left unaddressed in this version, either because they're out of scope for a single-user local app at this scale, or because fixing them is a natural (separable) follow-up:

- **Near-duplicate names aren't merged or prevented.** Trimming whitespace and rejecting blank names (Step 3) avoids the most accidental cases, but "Alex" and "alex" are still treated as two different players with no rename, delete, or merge option in this version. A mistyped name becomes a permanent, if harmless, extra profile.
- **No support for two instances of the app running at once.** This app is designed for a single user, one instance at a time, on one computer; simultaneous access to the same notebook file from two running copies of the app is untested and unsupported.
- **The rounds log has no pruning or archiving.** Every round ever played is kept forever. This is acceptable at this app's expected scale (one person, casual play) but would need revisiting if the notebook were ever expected to hold years of frequent play.
- **Timestamps are stored in local time**, with no timezone conversion or standardization. This is fine for a single-computer app but would need reconsideration if data were ever moved between machines in different timezones.

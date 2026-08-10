# Nutritional Tracking System - Context Log

*Instructions for the Team: Before starting an AI coding session, provide the AI with the most recent entries from this log. After you finish a feature, add a new entry to the top of this list before opening a Pull Request.*

---

## [2026-07-26] - Initial Setup (Suyash)
- **Action:** Created the GitHub repository, set up branch protection rules (require PRs for `main`).
- **Added:** `system_prompt.md`, `context_log.md`, `.gitignore`, and basic `README.md`.
- **Notes for AI / Team:** The project is initialized but empty. Next steps involve setting up the base FastAPI backend and initializing the React frontend boilerplate.

---
## [2026-07-31] - Phase 2: Auth & Target Generator (Suyash)
- **Added:** app/security.py, app/schemas.py, app/routers/auth.py, app/routers/users.py
- **Changed:** Restructured backend into app/ package (was flat files in backend/ root);
  login now uses OAuth2PasswordRequestForm instead of JSON body so Swagger's Authorize
  button works natively — schemas.UserLogin is now unused as a result; CORS origin set
  to http://localhost:5173 (Vite), not 3000
- **Notes for AI:** Auth uses JWT via python-jose + passlib (bcrypt pinned to 4.0.1 —
  newer bcrypt breaks passlib 1.7.4's version detection). Config values (DB URL, JWT
  secret) read via os.getenv() + python-dotenv, not pydantic-settings, to match existing
  database.py style — no config.py file. GET /users/me/targets computes calorie/macro
  targets via Mifflin-St Jeor + WHO/FAO AMDR midpoints (protein 12%, fat 28%, carbs 60%);
  activity factor is hardcoded to 1.375 (light activity) as a placeholder since users
  table has no activity_level column yet — revisit if per-user accuracy matters later.
  models.py already had DailyLog model + user/logs relationship in place before this
  phase (not new work).
<!-- 
TEMPLATE FOR NEW ENTRIES:
## [YYYY-MM-DD] - Feature Name (Your Name)
- **Added:** [What files/components did you create?]
- **Changed:** [What existing logic did you modify?]
- **Notes for AI:** [What should the next person/AI know? e.g., "Use the new /api/food route for the search bar"]
-->
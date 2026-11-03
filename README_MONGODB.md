# Optional MongoDB Atlas storage (local LeadFinder)

LeadFinder remains a local desktop application. Its HTTP server, API routes,
browser UI, and daily background scheduler continue to run on your computer.
MongoDB is an optional persistence mirror for the Python assistant's existing
JSON-backed state.

## Setup

1. In this repository, install the optional dependency:

   `python3 -m pip install -r requirements.txt`

2. Copy `.env.example` to `.env`.
3. Set `MONGODB_URI` to the connection string for your personal Atlas cluster.
4. Optionally set `MONGODB_DATABASE` (default: `leadfinder`).
5. Run the app as usual: `python3 leadfinder.py`.

Do not commit `.env` or paste the connection string into source code.

## Data behavior

- Existing local JSON files in `data/` are preserved.
- When Atlas is reachable, assistant state is read from the `app_state`
  collection and writes are mirrored to both Atlas and local JSON.
- Existing JSON files are automatically copied to Atlas on first read when
  the corresponding Atlas record does not exist.
- If Atlas is not configured or temporarily unavailable, LeadFinder continues
  using local JSON. A warning is printed in the terminal.
- The browser CRM list remains in browser localStorage; this change does not
  upload that list to Atlas.
- Atlas is not a substitute for a local backup. Keep the ignored `data/`
  folder backed up securely.

This implementation is intended for one personal local installation, not a
public multi-user hosted service.

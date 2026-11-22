# Changes

## 2026-11-22
- Channel "Malaysia Student Life" (@malaysiastudentlife1), owner request: 3 Shorts a day like the approved demo
  (Urdu voice, Roman Urdu captions, numbered cards on a Malaysia map, WhatsApp card at the end).
- Facts only from msl/facts.json (checked against EMGS, Immigration Department of Malaysia and university pages on 22 Nov).
  Gemini writes the lines from those facts; a second pass checks them; numbers that are not in the facts are rejected.
- Daily run 17:20 MY (backup 19:50 MY, skips if done). Uploads are private and go public at 12:00, 15:00, 17:30 UTC
  (5 pm, 8 pm, 10:30 pm Pakistan time).
- Shared engine: empire-maps-pipeline at a pinned commit (src/gemini.js, voice.js, youtube.js, geo.py, fonts). Nothing of
  Empire Maps is changed by this repo.

# Changes

## 2026-11-24 (16:30 MY) More topics, better titles (owner: "is ma khuch change karna hai to karo")
- Only 12 topics meant repeats from 26 Nov (on Empire Maps repeats got 3-7x fewer views). Added 8 new fact-checked
  topics: graduate_pass, mis_scholarship, visa_fees, foundation, muslim_friendly, dependants, insurance, language
  (sources listed in facts.json, checked 24 Nov). New/popular ones are first among the unused topics.
- Title prompt: use words Pakistani/Indian students search ("from Pakistan", "2026") when natural, vary the format,
  and differ from the last 9 titles.

## 2026-11-22
- Channel "Malaysia Student Life" (@malaysiastudentlife1), owner request: 3 Shorts a day like the approved demo
  (Urdu voice, Roman Urdu captions, numbered cards on a Malaysia map, WhatsApp card at the end).
- Facts only from msl/facts.json (checked against EMGS, Immigration Department of Malaysia and university pages on 22 Nov).
  Gemini writes the lines from those facts; a second pass checks them; numbers that are not in the facts are rejected.
- Daily run 17:20 MY (backup 19:50 MY, skips if done). Uploads are private and go public at 12:00, 15:00, 17:30 UTC
  (5 pm, 8 pm, 10:30 pm Pakistan time).
- Shared engine: empire-maps-pipeline at a pinned commit (src/gemini.js, voice.js, youtube.js, geo.py, fonts). Nothing of
  Empire Maps is changed by this repo.

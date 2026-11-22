'use strict';
// Malaysia Student Life: makes N Shorts (default 3) like the approved demo and uploads them as private with a
// scheduled publish time. Facts come ONLY from msl/facts.json (checked by hand against EMGS / Immigration / university
// pages). Gemini writes the lines from those facts, a second Gemini pass checks them, and any number not in the facts
// is rejected. Uses the shared engine (empire-maps-pipeline, pinned) for Gemini, voice and upload helpers.
// Usage: node msl/make.js [--count 3] [--no-upload] [--topic id]
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const ENGINE = process.env.ENGINE_DIR || path.join(ROOT, 'engine');
const { askJSON } = require(path.join(ENGINE, 'src', 'gemini'));
const { makeVoice } = require(path.join(ENGINE, 'src', 'voice'));
const { env, log, run, fetchRetry, FFMPEG, PYTHON } = require(path.join(ENGINE, 'src', 'lib'));

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const COUNT = Number(opt('--count', '3'));
const NO_UPLOAD = args.includes('--no-upload');
const FACTS = JSON.parse(fs.readFileSync(path.join(__dirname, 'facts.json'), 'utf8'));
const HIST = path.join(ROOT, 'history.json');
const readHist = () => { try { return JSON.parse(fs.readFileSync(HIST, 'utf8')); } catch (_) { return []; } };
const WHATSAPP = env('WHATSAPP', '+60 11-2835 7365');
const CHANNEL = 'https://youtube.com/@malaysiastudentlife1?sub_confirmation=1';
// publish times (UTC): 12:00, 15:00, 17:30 = 5 pm, 8 pm, 10:30 pm Pakistan time
const SLOTS = env('PUBLISH_SLOTS_UTC', '12:00,15:00,17:30').split(',').map(s => s.trim());

const CTA = {
  kind: 'cta', title: 'ADMISSION HELP', contact: `WhatsApp: ${WHATSAPP}`, detail: 'Free guidance — number description mein',
  urdu: 'داخلے اور ویزا میں مدد کے لیے ڈسکرپشن میں دیے گئے نمبر پر واٹس ایپ کریں۔',
  caption: 'Admission aur visa mein madad ke liye description mein diye number par WhatsApp karein.',
};

function pickTopics(n) {
  const want = opt('--topic', '');
  const h = readHist();
  const last = {};
  h.forEach((x, i) => { last[x.topic] = i; });
  const order = FACTS.topics.slice().sort((a, b) => (last[a.id] ?? -1) - (last[b.id] ?? -1));
  if (want) { const t = FACTS.topics.find(x => x.id === want); if (t) order.unshift(t); }
  return order.slice(0, n).map(t => ({ ...t, used: h.filter(x => x.topic === t.id).map(x => x.title) }));
}

const digits = s => (String(s).match(/\d+/g) || []);

function prompt(t) {
  return `You write YouTube Shorts for "Malaysia Student Life", a channel that helps students from Pakistan and India who want to study in Malaysia.
Topic: ${t.name}
FACTS (the ONLY information you may use; do not add any other fact, number, date, fee or promise):
${t.facts.map((f, i) => `${i + 1}. ${f}`).join('\n')}
${t.used.length ? `Titles already used for this topic (make a DIFFERENT angle/hook): ${t.used.join(' | ')}` : ''}

Make one Short of about 35-45 seconds: a hook card, then 3 to 5 numbered point cards, optionally 1 warning card. (A WhatsApp card is added after yours automatically.)
For EVERY card give:
- "urdu": the narration line in natural spoken Urdu (Urdu script), short (max 22 words). Write numbers as digits (7, 20, 6).
- "caption": the SAME line in simple Roman Urdu (as Pakistanis text), max 18 words, same numbers as digits.
- "title": 1-4 WORDS in English CAPITALS for the card (e.g. "OFFER LETTER").
- "detail": one short line in Roman Urdu/English mix for the card (max 12 words). Hook card: "badge" instead of detail (2-4 words, e.g. "5 ASAAN STEPS").
Card kinds: "title" (first card), "step" (numbered points, with "n": 1,2,3...), "warn" (optional, a common mistake).
Tone: friendly, clear, honest. No guarantees ("100% visa" etc.), no fees or numbers that are not in the facts, no politics.

Return ONLY JSON:
{"title": "English YouTube title under 70 characters with 1 emoji (e.g. 🇲🇾), searchable", "summary": "2 English sentences for the description", "tags": [8 to 12 English search tags], "hashtags": [3 hashtags like "#StudyInMalaysia"], "scenes": [cards in order]}`;
}

function validate(t, s) {
  const sc = Array.isArray(s.scenes) ? s.scenes : [];
  if (sc.length < 4 || sc.length > 8) throw new Error(`bad card count ${sc.length}`);
  if (sc[0].kind !== 'title') throw new Error('first card is not the hook');
  let n = 0;
  for (const c of sc) {
    if (!c.urdu || !c.caption || !c.title) throw new Error('card missing text');
    if (!['title', 'step', 'warn'].includes(c.kind)) throw new Error('bad card kind ' + c.kind);
    if (c.kind === 'step') c.n = ++n;
    if (c.caption.split(/\s+/).length > 22) throw new Error('caption too long');
  }
  // every number must come from the facts (step numbers and the step count are fine)
  const allowed = new Set([...digits(t.facts.join(' ')), ...Array.from({ length: 9 }, (_, i) => String(i + 1))]);
  for (const c of sc) {
    for (const d of [...digits(c.caption), ...digits(c.title), ...digits(c.detail || ''), ...digits(c.badge || '')]) {
      if (!allowed.has(d)) throw new Error(`number ${d} is not in the facts`);
    }
  }
  if (!s.title || s.title.length > 95) throw new Error('bad title');
  return sc;
}

async function writeScript(t) {
  let last;
  for (let a = 1; a <= 3; a++) {
    try {
      const s = await askJSON(prompt(t), { temperature: 0.8 });
      const sc = validate(t, s);
      const chk = await askJSON(`You check a short video script against a list of facts. FACTS:\n${t.facts.map(f => '- ' + f).join('\n')}\n\nLINES (Roman Urdu):\n${sc.map((c, i) => `${i + 1}. ${c.caption} [${c.title} / ${c.detail || c.badge || ''}]`).join('\n')}\n\nIs every line fully supported by the facts (no extra claim, number or promise)? A friendly hook question is fine.\nReturn ONLY JSON: {"ok": true or false, "problems": ["line number: what is wrong"]}`, { temperature: 0.1 });
      if (chk.ok === false && (chk.problems || []).length) throw new Error('fact check: ' + chk.problems.join('; ').slice(0, 300));
      s.scenes = sc;
      return s;
    } catch (e) { last = e; log(`Script try ${a} for ${t.id} not usable: ${e.message}`); }
  }
  throw last;
}

function nextSlot(i, taken) {
  const now = Date.now();
  for (let day = 0; day < 3; day++) {
    for (const hm of SLOTS) {
      const [hh, mm] = hm.split(':').map(Number);
      const d = new Date(); d.setUTCDate(d.getUTCDate() + day); d.setUTCHours(hh, mm || 0, 0, 0);
      const iso = d.toISOString().replace(/\.\d{3}Z$/, 'Z');
      if (d.getTime() > now + 25 * 60000 && !taken.has(iso)) return iso;
    }
  }
  return new Date(now + (30 + i * 60) * 60000).toISOString().replace(/\.\d{3}Z$/, 'Z');
}

async function upload(file, meta, publishAt) {
  const { accessToken } = require(path.join(ENGINE, 'src', 'youtube'));
  const token = await accessToken();
  const size = fs.statSync(file).size;
  const body = {
    snippet: { title: meta.title, description: meta.description, tags: meta.tags.slice(0, 15), categoryId: '27', defaultLanguage: 'ur', defaultAudioLanguage: 'ur' },
    status: { privacyStatus: 'private', publishAt, selfDeclaredMadeForKids: false, containsSyntheticMedia: false },
  };
  const start = await fetchRetry('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json; charset=UTF-8', 'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': String(size) },
    body: JSON.stringify(body),
  });
  if (!start.ok) throw new Error(`upload start HTTP ${start.status}: ${(await start.text()).slice(0, 400)}`);
  const put = await fetch(start.headers.get('location'), { method: 'PUT', headers: { 'Content-Type': 'video/mp4', 'Content-Length': String(size) }, body: fs.readFileSync(file) });
  const text = await put.text();
  if (!put.ok) throw new Error(`upload HTTP ${put.status}: ${text.slice(0, 400)}`);
  return JSON.parse(text).id;
}

async function main() {
  const today = new Date().toISOString().slice(0, 10);
  const hist = readHist();
  const doneToday = hist.filter(h => h.date.slice(0, 10) === today && h.videoId).length;
  if (!NO_UPLOAD && !args.includes('--force') && doneToday >= COUNT) { log(`Already ${doneToday} videos today, nothing to do.`); return; }
  const need = NO_UPLOAD ? COUNT : COUNT - doneToday;
  const topics = pickTopics(need);
  const taken = new Set(hist.map(h => h.publishAt).filter(Boolean));
  let made = 0;
  for (let i = 0; i < topics.length; i++) {
    const t = topics[i];
    try {
      log(`--- Short ${i + 1}/${topics.length}: ${t.name}`);
      const s = await writeScript(t);
      const scenes = [...s.scenes, CTA];
      const dir = path.join(ROOT, 'output', `${today}-${i + 1}-${t.id}`);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, 'script.json'), JSON.stringify(s, null, 2));
      const voice = await makeVoice({ lines: scenes.map(c => c.urdu) }, dir, i);
      if (!voice) throw new Error('no voice');
      const spec = { scenes, segments: voice.segments, voice: voice.file, lead: 0.6, total: 0.6 + voice.dur + 1.2, engine: ENGINE,
        data_dir: path.join(ROOT, 'data'), out: path.join(dir, 'short.mp4'), work: dir, ffmpeg: FFMPEG(), brand: 'MALAYSIA STUDENT LIFE' };
      fs.writeFileSync(path.join(dir, 'spec.json'), JSON.stringify(spec, null, 1));
      const o = await run(PYTHON(), [path.join(__dirname, 'render.py'), path.join(dir, 'spec.json')]);
      if (o.trim()) log(o.trim());
      const tags = (s.tags || []).concat(['study in malaysia', 'malaysia student visa', 'malaysia student life']);
      const description = `${s.summary || ''}\n\n📩 Admission & visa help — WhatsApp: ${WHATSAPP}\n🔔 Subscribe for more Malaysia study tips: ${CHANNEL}\n\nInformation checked from official sources (EMGS, Immigration Department of Malaysia, universities). Rules can change — always confirm with your university before you apply.\n\n${(s.hashtags || ['#StudyInMalaysia', '#MalaysiaStudentVisa', '#Shorts']).slice(0, 4).join(' ')}`;
      fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify({ title: s.title, description, tags }, null, 2));
      const entry = { date: new Date().toISOString(), topic: t.id, title: s.title };
      if (!NO_UPLOAD) {
        const publishAt = nextSlot(i, taken);
        taken.add(publishAt);
        entry.videoId = await upload(spec.out, { title: s.title, description, tags }, publishAt);
        entry.publishAt = publishAt;
        log(`Uploaded https://youtube.com/shorts/${entry.videoId} — goes public at ${publishAt}`);
        const h = readHist(); h.push(entry); fs.writeFileSync(HIST, JSON.stringify(h, null, 2));
      }
      made++;
    } catch (e) { log(`Short ${i + 1} failed: ${e.message}`); }
  }
  if (!made) { log('FAILED: no video made'); process.exit(1); }
}

main().catch(e => { log('FAILED: ' + (e.stack || e.message)); process.exit(1); });

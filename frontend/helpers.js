"use strict";
/* ---------- layout constants ---------- */
const HEADER_H = 56, LINE_H = 20, PAD_Y = 4;     // row height = lines*20 + 8
// PAD_X reserves room in every auto-width column for the header controls
// (sort arrow + pin button + hide button) so the column name is not covered by them.
const MAXLINES = 6, CHAR_PX = 7, MIN_COL = 128, MAX_COL = 460, HEAD_MAX_COL = 288, PAD_X = 76, BUFFER_PX = 140;

/* ---------- API endpoints ---------- */
const API = {
  upload:    "/api/upload",
  pick:      "/api/pick",
  open:      "/api/open",
  data:      "/api/data",
  meta:      "/api/meta",
  history:   "/api/history",
  histClear: "/api/history/clear",
  histRemove:"/api/history/remove",
  samples:   "/api/samples",
  openNative:"/api/open-native",
  reveal:    "/api/reveal",
};

/* ---------- small helpers (no Vue dependency) ---------- */
function clearReactive(obj){ Object.keys(obj).forEach(k => delete obj[k]); }

/* subtle per-column tints (header slightly stronger) */
const CELL_TINTS = ["#f4f8fd","#f7f2fb","#f1faf3","#fdf7f1","#fdf2f3","#eef5f9","#f6f9ee","#eef8f4","#f9eef6","#f1f4f8"];
const HEAD_TINTS = ["#e2ecfa","#ead8f2","#d8efdd","#f1e2cf","#f1dde0","#d9e6ef","#e6ecd7","#d7ebe1","#e9d8e8","#dde3ea"];

/* ---------- helpers ---------- */
function dispWidth(s){
  let w = 0;
  for (const ch of String(s)){
    const c = ch.codePointAt(0);
    w += (c >= 0x1100 && (c <= 0x115F || (c >= 0x2E80 && c <= 0xA4CF) || (c >= 0xAC00 && c <= 0xD7A3) ||
        (c >= 0xF900 && c <= 0xFAFF) || (c >= 0xFE30 && c <= 0xFE4F) || (c >= 0xFF00 && c <= 0xFF60) ||
        (c >= 0xFFE0 && c <= 0xFFE6))) ? 2 : 1;
  }
  return w;
}
function lowerBound(arr, v){
  let lo = 0, hi = arr.length;
  while (lo < hi){ const m = (lo + hi) >> 1; if (arr[m] < v) lo = m + 1; else hi = m; }
  return lo;
}
/* A value is "numeric" only if it is a pure number (int/float, optional sign /
   exponent). This deliberately EXCLUDES things like "2026-07-03" or
   "2026-07-03 12:02:30", whose leading number is just the year — those must be
   compared as strings, which sorts ISO dates/datetimes chronologically. */
function isStrictNumber(s){
  return /^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(s.trim());
}
async function getJSON(url, opts){
  const signal = opts && opts.signal;
  const r = await fetch(url, { signal });
  if (!signal || !r.body){
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
    return j;
  }
  // Streaming response with an abort signal: pull the body chunk by chunk so a
  // cancel that lands while a large payload is still in flight is honoured
  // promptly (the fetch signal aborts reader.read() too, but we also check
  // between chunks). The final JSON.parse is synchronous and briefly uninterruptible.
  const reader = r.body.getReader();
  const chunks = []; let total = 0;
  for (;;){
    if (signal.aborted){ try{ reader.cancel(); }catch(_){} const e = new Error("aborted"); e.name = "AbortError"; throw e; }
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); total += value.length;
  }
  const merged = new Uint8Array(total);
  let off = 0;
  for (const c of chunks){ merged.set(c, off); off += c.length; }
  const j = JSON.parse(new TextDecoder().decode(merged));
  if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
  return j;
}
async function postJSON(url, body, opts){
  const r = await fetch(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body), signal: opts && opts.signal});
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
  return j;
}
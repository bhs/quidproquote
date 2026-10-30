"""The labelling page: one self-contained HTML file a person opens in a browser.

It embeds the blind sheet (exact caption words and donor wording with their sources, nothing about
any method), shows one pair at a time in an order that depends on the labeler's name, times each
label, saves progress in the browser, and downloads a JSON file to put in person_labels/.
"""

import json

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Label quote and priority pairs</title>
<style>
body{font:16px/1.5 system-ui,sans-serif;max-width:56rem;margin:1rem auto;padding:0 1rem;color:#1b1b1b}
.box{border:1px solid #bbb;border-radius:6px;padding:.75rem 1rem;margin:.75rem 0;background:#fafafa}
.quote{font-family:ui-monospace,Menlo,monospace;font-size:15px}
.meta{color:#555;font-size:14px}
fieldset{border:1px solid #ccc;border-radius:6px;margin:.6rem 0}
label{margin-right:1.2rem;white-space:nowrap}
button{font-size:16px;padding:.4rem 1rem}
#bar{height:6px;background:#ddd;border-radius:3px}#bar div{height:6px;background:#2a6;border-radius:3px}
.hint{color:#555;font-size:14px}
</style></head><body>
<h1>Label quote and priority pairs</h1>
<div id="start">
<p>Each pair is a passage from the raw live captions of a San Francisco government meeting and a priority statement
that a donor published about itself. You say whether they overlap, whether they take the same side, and who seems to be
speaking. Each label is timed, from the moment a pair appears until you press Next.</p>
<ul>
<li><b>real</b>: the passage speaks to the same specific measure, program, proposal or stated position as the priority,
so you can see why the two sit side by side.</li>
<li><b>loose</b>: the same broad subject only, with no shared specific proposal or position.</li>
<li><b>none</b>: different subjects, even if some words or numbers are shared.</li>
</ul>
<p>The captions are in capitals and garble names, numbers and words such as aye and no. Read them as spoken. The caption
words just before the passage are one click away; open the transcript link if you want to check the recording, and take
as long as you would really take.</p>
<p><label>Your name or initials: <input id="name" size="20"></label></p>
<p><label><input type="checkbox" id="attest"> I am a person, not an automated reader, and I have not seen any method's
output, any earlier labels or any results file for these pairs.</label></p>
<p><button id="go">Start</button> <span class="hint">Progress is saved in this browser; you can stop and come back with the same name.</span></p>
</div>
<div id="work" hidden>
<div id="bar"><div style="width:0"></div></div>
<p class="meta" id="count"></p>
<div class="box"><b>Passage</b> <span class="meta" id="qmeta"></span>
<p class="quote" id="qtext"></p>
<details><summary>Caption words just before the passage (may name the speaker)</summary><p class="quote" id="qbefore"></p></details></div>
<div class="box"><b>Donor priority</b> <span class="meta" id="pmeta"></span>
<p id="ptext"></p></div>
<fieldset><legend>1. Overlap (keys 1, 2, 3)</legend>
<label><input type="radio" name="ov" value="real"> real</label>
<label><input type="radio" name="ov" value="loose"> loose</label>
<label><input type="radio" name="ov" value="none"> none</label></fieldset>
<fieldset id="side"><legend>2. Do the passage and the priority take the same side? (keys 4, 5, 6)</legend>
<label><input type="radio" name="sd" value="same"> same side</label>
<label><input type="radio" name="sd" value="opposite"> opposite sides</label>
<label><input type="radio" name="sd" value="unclear"> neither takes a side, or can't tell</label></fieldset>
<fieldset id="spk"><legend>3. Who seems to be speaking? (keys 7, 8, 9)</legend>
<label><input type="radio" name="sp" value="official"> an elected official, for themselves</label>
<label><input type="radio" name="sp" value="other"> someone else (clerk, public comment, staff, applicant)</label>
<label><input type="radio" name="sp" value="unclear"> can't tell</label></fieldset>
<p><input id="note" size="60" placeholder="optional note"> <button id="next">Next (Enter)</button>
<button id="save" type="button">Download labels so far</button></p>
</div>
<div id="done" hidden><h2>Finished</h2>
<p>Download the file and give it to whoever runs the check; it goes in <code>labelling/person_labels/</code>.</p>
<p><button id="dl">Download labels</button></p></div>
<script>
const SHEET = __SHEET__;
const $ = id => document.getElementById(id);
let who = "", order = [], pos = 0, state = null, shownAt = 0, hiddenMs = 0, hiddenAt = null;
function hash(s){let h=1779033703^s.length;for(let i=0;i<s.length;i++){h=Math.imul(h^s.charCodeAt(i),3432918353);h=h<<13|h>>>19}return h>>>0}
function rng(seed){return function(){seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function shuffled(ids,name){const r=rng(hash(name));const a=ids.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(r()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
const byId = {}; SHEET.pairs.forEach(p => byId[p.pair] = p);
function key(){return "pairlabels:" + who}
function save(){localStorage.setItem(key(), JSON.stringify(state))}
document.addEventListener("visibilitychange", () => {
  if (document.hidden) hiddenAt = Date.now();
  else if (hiddenAt) { hiddenMs += Date.now() - hiddenAt; hiddenAt = null; }
});
function show(){
  if (pos >= order.length) { $("work").hidden = true; $("done").hidden = false; download(); return; }
  const p = byId[order[pos]];
  $("count").textContent = "Pair " + (pos + 1) + " of " + order.length;
  $("bar").firstElementChild.style.width = (100 * pos / order.length) + "%";
  $("qmeta").innerHTML = "(" + esc(p.quote.meeting) + ", caption time " + esc(p.quote.stamp) + ", <a target=_blank rel=noopener href='" + esc(p.quote.url) + "'>transcript</a>)";
  $("qtext").textContent = p.quote.text;
  $("qbefore").textContent = p.quote.before || "(none)";
  $("pmeta").innerHTML = "(" + esc(p.priority.donor) + (p.priority.section ? ", section: " + esc(p.priority.section) : "") + ", <a target=_blank rel=noopener href='" + esc(p.priority.url) + "'>source</a>, retrieved " + esc(p.priority.retrieved) + ")";
  $("ptext").textContent = p.priority.text;
  document.querySelectorAll("input[type=radio]").forEach(r => r.checked = false);
  $("note").value = ""; $("qbefore").parentElement.open = false; syncVisibility();
  hiddenMs = 0; hiddenAt = document.hidden ? Date.now() : null; shownAt = Date.now();
}
function esc(s){return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function val(n){const r=document.querySelector("input[name="+n+"]:checked");return r?r.value:null}
function syncVisibility(){const none = val("ov") === "none"; $("side").style.opacity = $("spk").style.opacity = none ? .4 : 1}
function next(){
  const ov = val("ov"), sd = val("sd"), sp = val("sp");
  if (!ov || (ov !== "none" && (!sd || !sp))) { alert("Please answer every question (side and speaker may be skipped when the overlap is none)."); return; }
  const now = Date.now(), id = order[pos];
  if (hiddenAt) { hiddenMs += now - hiddenAt; hiddenAt = null; }
  state.labels[id] = ov;
  if (ov !== "none") { state.sides[id] = sd; state.speakers[id] = sp; } else { delete state.sides[id]; delete state.speakers[id]; }
  state.ms[id] = now - shownAt; state.ms_hidden[id] = hiddenMs;
  if ($("note").value.trim()) state.notes[id] = $("note").value.trim();
  pos++; state.pos = pos; save(); show();
}
function download(){
  const doc = {format: 1, labeler: who, blind: true, sheet_built: SHEET.built, order: order,
    labels: state.labels, sides: state.sides, speakers: state.speakers, ms: state.ms, ms_hidden: state.ms_hidden, notes: state.notes};
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(doc, null, 1)], {type: "application/json"}));
  a.download = who.replace(/[^A-Za-z0-9_-]+/g, "_") + ".json"; a.click();
}
$("go").onclick = () => {
  who = $("name").value.trim();
  if (!who) { alert("Please enter your name or initials."); return; }
  if (!$("attest").checked) { alert("This check only counts labels made without seeing any output."); return; }
  const saved = localStorage.getItem(key());
  state = saved ? JSON.parse(saved) : {labels: {}, sides: {}, speakers: {}, ms: {}, ms_hidden: {}, notes: {}, pos: 0};
  order = shuffled(SHEET.pairs.map(p => p.pair), who); pos = Math.min(state.pos || 0, order.length);
  $("start").hidden = true; $("work").hidden = false; show();
};
$("next").onclick = next; $("save").onclick = download; $("dl").onclick = download;
document.addEventListener("change", syncVisibility);
document.addEventListener("keydown", e => {
  if ($("work").hidden || e.target.id === "note") return;
  const map = {"1":["ov","real"],"2":["ov","loose"],"3":["ov","none"],"4":["sd","same"],"5":["sd","opposite"],"6":["sd","unclear"],
               "7":["sp","official"],"8":["sp","other"],"9":["sp","unclear"]};
  if (map[e.key]) { const [n, v] = map[e.key]; document.querySelector("input[name="+n+"][value="+v+"]").checked = true; syncVisibility(); }
  else if (e.key === "Enter") next();
});
</script></body></html>
"""


def build_html(sheet):
    """The labelling page with the sheet embedded. '<' is escaped so a caption cannot close the script tag."""
    data = json.dumps(sheet, ensure_ascii=False).replace("<", "\\u003c")
    return PAGE.replace("__SHEET__", data)

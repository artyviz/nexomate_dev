// Simulated lead-to-customer workflow engine (no real integrations).
const PHASES = [
  { title: "1 · Capture", nodes: ["arrive", "crm", "instant"] },
  { title: "2 · Engage", nodes: ["responds", "ai", "followup", "later", "unresponsive"] },
  { title: "3 · Qualify & Score", nodes: ["qualify", "unqualified", "score", "priority"] },
  { title: "4 · Route", nodes: ["handoff", "nurture", "longterm"] },
  { title: "5 · Appointment", nodes: ["invite", "booked", "confirm", "bookreminder", "reminders", "attended", "sales", "noshow"] },
  { title: "6 · Close", nodes: ["proposal", "decision", "won", "quotefollow", "lost"] },
  { title: "7 · Retain", nodes: ["onboard", "review", "referral", "upsell", "reactivate", "end"] },
];

const L = (text) => ({ from: "lead", text });
const A = (text) => ({ from: "ai", text });
const S = (text) => ({ from: "sys", text });

// label, decision?, log text, optional chat + CRM updates
const NODES = {
  arrive: { label: "Lead Arrives", log: (c) => `New lead received via ${c.source}.`, crm: { Status: "New" }, chat: (c) => [S(`Lead arrived from ${c.source}`)] },
  crm: { label: "Create / Update CRM", log: () => "Lead record created in CRM and de-duplicated.", crm: { Status: "In CRM" } },
  instant: { label: "Instant Response", log: () => "Instant response sent in under 5 seconds.", chat: () => [A("Hi Sarah! Thanks for reaching out to Brightside Dental 👋 I'm here to help — what are you looking for today?")] },
  responds: { label: "Lead Responds?", d: 1, log: (c) => (c.responds ? "Lead replied – starting AI conversation." : "No reply yet – starting follow-up sequence.") },
  ai: { label: "AI Conversation", log: () => "AI assistant is engaging and gathering needs.", crm: { Status: "Engaged" },
    chat: () => [L("I want teeth whitening, how much is it and how soon can I come?"), A("Great choice! Whitening starts at $299. May I ask your budget and ideal timeframe?"), L("Budget is fine, I'd like to do it this week.")] },
  followup: { label: "Automated Follow-up", log: () => "Follow-up sequence: SMS +1h, email +24h, WhatsApp +48h.", chat: () => [S("No response…"), A("Hi Sarah, just checking in — still interested in whitening? 😊")] },
  later: { label: "Responds Later?", d: 1, log: (c) => (c.laterReply ? "Lead replied to follow-up." : "No reply after full sequence.") },
  unresponsive: { label: "Unresponsive / Nurture", log: () => "Marked unresponsive and moved to nurture list.", crm: { Status: "Unresponsive" } },
  qualify: { label: "Qualification", d: 1, log: (c) => (c.qualified ? "Lead meets budget, need and timeline criteria." : "Lead does not meet criteria (budget / location)."), crm: { Status: "Qualifying" } },
  unqualified: { label: "Mark Unqualified", log: () => "Lead marked unqualified and archived.", crm: { Status: "Unqualified" } },
  score: { label: "Lead Scoring", log: (c) => `AI lead score calculated: ${c.score}/100.`, crm: (c) => ({ Score: c.score }) },
  priority: { label: "Lead Priority", d: 1, log: (c) => `Priority assigned: ${c.priority}.`, crm: (c) => ({ Priority: c.priority }) },
  handoff: { label: "Sales Handoff", log: () => "🔔 Instant notification sent to sales team. Human takes over.", crm: { Status: "With Sales" }, chat: () => [S("Sales rep Alex joined the conversation")] },
  nurture: { label: "Nurture + Follow-up", log: () => "Warm lead placed in nurture + follow-up cadence.", crm: { Status: "Nurturing" } },
  longterm: { label: "Long-term Nurture", log: () => "Cold lead added to long-term nurture with periodic re-engagement.", crm: { Status: "Long-term Nurture" } },
  invite: { label: "Appointment Invitation", log: () => "Booking link sent to lead.", chat: () => [A("Shall I book you in? Pick a slot: Thu 3:00 PM · Fri 11:00 AM")] },
  booked: { label: "Appointment Booked?", d: 1, log: (c) => (c.booked ? "Lead booked Thu 3:00 PM." : "Lead has not booked.") },
  confirm: { label: "Confirmation", log: () => "Confirmation sent via email + SMS; calendar invite added.", crm: { Status: "Booked" }, chat: () => [L("Thursday 3 PM works!"), A("Confirmed ✅ See you Thursday at 3:00 PM.")] },
  bookreminder: { label: "Booking Reminder", log: () => "Booking reminder sent; lead stays in follow-up.", chat: () => [A("Your slot is still open — want me to hold Thursday 3 PM for you?")] },
  reminders: { label: "Appointment Reminders", log: () => "Reminders sent: 24h and 2h before.", chat: () => [A("Reminder: your appointment is tomorrow at 3:00 PM ⏰")] },
  attended: { label: "Attended?", d: 1, log: (c) => (c.attended ? "Lead attended the appointment." : "Lead did not show up.") },
  noshow: { label: "No-show Recovery", log: () => "No-show recovery message sent with reschedule link.", crm: { Status: "No-show" }, chat: () => [A("We missed you today! Want to reschedule? 🗓️")] },
  sales: { label: "Sales Conversation", log: () => "Consultation completed by sales rep.", crm: { Status: "In Consultation" } },
  proposal: { label: "Proposal / Quote", log: () => "Proposal of $1,450 sent to customer.", crm: { Value: "$1,450" }, chat: () => [S("Proposal sent: Whitening + Cleaning package — $1,450")] },
  decision: { label: "Customer Decision", d: 1, log: (c) => (c.won ? "Customer accepted the proposal." : "No decision yet – quote follow-up triggered.") },
  quotefollow: { label: "Quote Follow-up", log: () => "Quote follow-up sent. Awaiting response.", chat: () => [A("Hi Sarah, any questions on the proposal? Happy to adjust.")] },
  lost: { label: "Lost / Nurture", log: () => "Deal marked lost; lead recycled to nurture.", crm: { Status: "Lost" } },
  won: { label: "Deal Won", log: () => "🎉 Deal won!", crm: { Status: "WON" }, chat: () => [L("Let's go ahead!"), S("Deal won – $1,450")] },
  onboard: { label: "Onboarding / Delivery", log: () => "Customer onboarded and service delivered.", crm: { Status: "Customer" } },
  review: { label: "Review Request", log: () => "Review request sent (Google).", chat: () => [A("Loved having you! Would you leave us a quick review? ⭐")] },
  referral: { label: "Referral Request", log: () => "Referral offer sent: $50 credit per friend." },
  upsell: { label: "Upsell / Repeat", log: () => "Upsell offer: 6-month whitening top-up." },
  reactivate: { label: "Reactivation Campaign", log: () => "Reactivation campaign scheduled for dormant leads." },
  end: { label: "Retention / Repeat Business", log: () => "Workflow complete. Customer retained for repeat business.", crm: { Status: "Retained" } },
};

const SCENARIOS = {
  hot: { name: "🔥 Hot lead → Won", cfg: { responds: true, qualified: true, score: 92, priority: "HOT", booked: true, attended: true, won: true },
    path: ["arrive","crm","instant","responds","ai","qualify","score","priority","handoff","invite","booked","confirm","reminders","attended","sales","proposal","decision","won","onboard","review","referral","upsell","reactivate","end"] },
  warm: { name: "🌤 Warm lead → Nurture", cfg: { responds: true, qualified: true, score: 63, priority: "WARM", booked: false },
    path: ["arrive","crm","instant","responds","ai","qualify","score","priority","nurture","invite","booked","bookreminder"] },
  cold: { name: "❄️ Cold lead → Long-term", cfg: { responds: true, qualified: true, score: 28, priority: "COLD" },
    path: ["arrive","crm","instant","responds","ai","qualify","score","priority","longterm"] },
  unresp: { name: "🔕 No response", cfg: { responds: false, laterReply: false },
    path: ["arrive","crm","instant","responds","followup","later","unresponsive"] },
  unqual: { name: "🚫 Unqualified", cfg: { responds: true, qualified: false },
    path: ["arrive","crm","instant","responds","ai","qualify","unqualified"] },
  noshow: { name: "😕 No-show recovery", cfg: { responds: true, qualified: true, score: 85, priority: "HOT", booked: true, attended: false },
    path: ["arrive","crm","instant","responds","ai","qualify","score","priority","handoff","invite","booked","confirm","reminders","attended","noshow"] },
  lost: { name: "📉 Quote not accepted", cfg: { responds: true, qualified: true, score: 88, priority: "HOT", booked: true, attended: true, won: false },
    path: ["arrive","crm","instant","responds","ai","qualify","score","priority","handoff","invite","booked","confirm","reminders","attended","sales","proposal","decision","quotefollow","lost"] },
};

const $ = (id) => document.getElementById(id);
let idx = -1, timer = null, ctx = {}, crmState = {};
const CRM_FIELDS = ["Name", "Source", "Status", "Score", "Priority", "Value"];

function buildFlow() {
  $("phases").innerHTML = PHASES.map((p) => `<div class="phase"><div class="phase-title">${p.title}</div><div class="nodes">` +
    p.nodes.map((n) => `<span class="node ${NODES[n].d ? "decision" : ""}" id="n-${n}">${NODES[n].label}</span>`).join("") +
    `</div></div>`).join("");
}

function renderCRM(changed = []) {
  $("leadCard").innerHTML = CRM_FIELDS.map((f) => {
    let v = crmState[f] ?? "—";
    if (f === "Priority" && crmState[f]) v = `<span class="badge ${v}">${v}</span>`;
    return `<div class="field ${changed.includes(f) ? "flash" : ""}"><small>${f}</small><span>${v}</span></div>`;
  }).join("");
}

function addMsg(m) {
  const chat = $("chat");
  if (chat.querySelector(".empty")) chat.innerHTML = "";
  const d = document.createElement("div");
  d.className = `msg ${m.from}`; d.textContent = m.text;
  chat.appendChild(d); chat.scrollTop = chat.scrollHeight;
}

function addLog(text) {
  const li = document.createElement("li");
  li.innerHTML = `<time>${new Date().toLocaleTimeString()}</time>${text}`;
  $("log").prepend(li);
}

function runStep() {
  const path = SCENARIOS[$("scenario").value].path;
  if (idx >= path.length - 1) return stop();
  if (idx >= 0) { const prev = $("n-" + path[idx]); prev.classList.remove("active"); prev.classList.add("done"); }
  idx++;
  const id = path[idx], n = NODES[id];
  $("n-" + id).classList.add("active");
  $("n-" + id).scrollIntoView({ block: "nearest", behavior: "smooth" });
  addLog(`<b>${n.label}</b> — ${n.log(ctx)}`);
  const upd = typeof n.crm === "function" ? n.crm(ctx) : n.crm;
  if (upd) { Object.assign(crmState, upd); renderCRM(Object.keys(upd)); }
  if (n.chat) n.chat(ctx).forEach((m, i) => setTimeout(() => addMsg(m), i * 450));
  if (idx >= path.length - 1) stop(true);
}

function stop(finished) {
  clearInterval(timer); timer = null;
  $("play").textContent = finished ? "↻ Replay" : "▶ Run demo";
  if (finished) {
    const last = $("n-" + SCENARIOS[$("scenario").value].path[idx]);
    last.classList.remove("active"); last.classList.add("done");
  }
}

function reset() {
  stop(); idx = -1;
  ctx = { ...SCENARIOS[$("scenario").value].cfg, source: $("source").value };
  crmState = { Name: "Sarah Johnson", Source: ctx.source };
  $("channelTag").textContent = ctx.source;
  $("chat").innerHTML = `<p class="empty">Press <b>Run demo</b> to start.</p>`;
  $("log").innerHTML = "";
  buildFlow(); renderCRM();
  $("play").textContent = "▶ Run demo";
}

$("play").onclick = () => {
  if (timer) return stop();
  if (idx >= SCENARIOS[$("scenario").value].path.length - 1 || idx === -1 && false) reset();
  $("play").textContent = "⏸ Pause";
  runStep();
  if (idx < SCENARIOS[$("scenario").value].path.length - 1) timer = setInterval(runStep, +$("speed").value);
};
$("step").onclick = () => { if (timer) stop(); if (idx >= SCENARIOS[$("scenario").value].path.length - 1) reset(); runStep(); };
$("reset").onclick = reset;
$("scenario").onchange = reset;
$("source").onchange = reset;
$("speed").onchange = () => { if (timer) { clearInterval(timer); timer = setInterval(runStep, +$("speed").value); } };

$("scenario").innerHTML = Object.entries(SCENARIOS).map(([k, s]) => `<option value="${k}">${s.name}</option>`).join("");
reset();

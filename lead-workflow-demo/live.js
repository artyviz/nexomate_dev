const $ = (id) => document.getElementById(id);
const STAGES = [["captured","Lead captured + CRM"],["engaged","AI conversation"],["qualified","Qualified"],["scored","Lead scored"],
  ["routed","Routed (Hot/Warm/Cold)"],["booked","Appointment booked"],["reminded","Reminders sent"],["attended","Attended"],
  ["proposal","Proposal / quote"],["won","Deal won"],["onboarded","Onboarding / delivery"],["review","Review + referral"],["retained","Upsell / retention"]];
const ACTIONS = [["followup","🔁 Send follow-up"],["reminder","⏰ Appt reminder"],["attended","🙋 Mark attended"],["noshow","😕 No-show"],
  ["proposal","💼 Send proposal"],["won","🏆 Deal won"],["lost","📉 Deal lost"],["onboard","🚀 Onboarded"],
  ["review","⭐ Review request"],["referral","🎁 Referral"],["upsell","➕ Upsell"],["reactivate","📣 Reactivate"]];
const FLAGS = { unresponsive: "Unresponsive → nurture", unqualified: "Unqualified", noshow: "No-show", lost: "Lost → nurture" };

let leadId = null, last = "", cfg = {}, typingTimer = null, entry = "form";
const ENTRY_HINT = { form: "Lead fills a form; bot greets first.", ad: "Lead taps 'Send Message' on a Facebook/Instagram ad; chat opens pre-filled and the bot replies instantly.",
  qr: "Lead scans a QR code (poster, shop, brochure) and lands in WhatsApp.", widget: "Lead clicks the website chat widget and continues on WhatsApp." };
const SENT = { positive: "😊 Positive", neutral: "😐 Neutral", frustrated: "😤 Frustrated", confused: "😕 Confused" };
const INTEREST = { interested: "🟢 Interested", prospect: "🟡 Prospect", not_interested: "⚪ Not interested" };

document.querySelectorAll("#entries .entry").forEach((b) => b.onclick = () => {
  entry = b.dataset.e;
  document.querySelectorAll("#entries .entry").forEach((x) => x.classList.toggle("on", x === b));
  $("entryHint").textContent = ENTRY_HINT[entry];
  const q = entry === "qr" || entry === "ad";
  $("qrcard").hidden = !(q && cfg.mode === "live" && cfg.whatsapp_ready);
  if (!$("qrcard").hidden) { $("qrimg").src = "https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=" + encodeURIComponent(cfg.wa_link); $("qrlink").href = cfg.wa_link; }
});

async function loadStats() {
  const s = await api("/stats");
  const card = (v, l) => `<div class="stat"><b>${v}</b><small>${l}</small></div>`;
  $("stats").innerHTML = card(s.leads, "Leads captured") + card(s.avg_response_s == null ? "—" : s.avg_response_s + "s", "Avg response time") +
    card(s.interested, "Interested") + card(s.hot, "HOT leads") + card(s.booked, "Demos booked") + card(s.conversion_pct + "%", "Lead → booked") + card(s.won, "Deals won");
}

async function api(path, method = "GET", body) {
  const r = await fetch("/api" + path, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function loadConfig() {
  cfg = await api("/config");
  $("biz").textContent = `${cfg.agent} · ${cfg.business}`;
  $("waTitle").textContent = `${cfg.agent} · ${cfg.business}`;
  const live = cfg.mode === "live";
  $("modeToggle").classList.toggle("live", live);
  document.querySelectorAll("#modeToggle button").forEach((b) => b.classList.toggle("on", b.dataset.mode === cfg.mode));
  const chip = (el, ok, label) => { el.textContent = label; el.className = "chip " + (ok ? "ok" : "warn"); };
  chip($("chipWa"), cfg.whatsapp_ready, "WhatsApp: " + (cfg.whatsapp_ready ? "Twilio ready" : "not configured"));
  chip($("chipEm"), cfg.email_ready, "Email: " + (cfg.email_ready ? "SMTP ready" : "not configured"));
  chip($("chipAi"), cfg.llm === "groq", "AI: " + (cfg.llm === "groq" ? "Groq LLM" : "scripted"));
  $("autoFu").checked = cfg.auto_followup;
}

document.querySelectorAll("#modeToggle button").forEach((b) => b.onclick = async () => { await api("/config", "POST", { mode: b.dataset.mode }); loadConfig(); });
$("autoFu").onchange = (e) => api("/config", "POST", { auto_followup: e.target.checked });

$("actions").innerHTML = ACTIONS.map(([k, l]) => `<button class="btn" data-a="${k}" disabled>${l}</button>`).join("");
$("actions").onclick = async (e) => { const a = e.target.dataset.a; if (a && leadId) { await api(`/leads/${leadId}/action`, "POST", { action: a }); poll(); } };

$("createLead").onclick = async () => {
  const channels = [$("chWa").checked && "whatsapp", $("chEm").checked && "email"].filter(Boolean);
  if (!channels.length) return alert("Pick at least one channel");
  $("createLead").disabled = true;
  try {
    const lead = await api("/leads", "POST", { name: $("fName").value, company: $("fCompany").value, phone: $("fPhone").value, email: $("fEmail").value,
      source: $("fSource").value, entry, channels });
    leadId = lead.id; last = "";
    $("waText").disabled = false; document.querySelector("#waForm button").disabled = false;
    const em = channels.includes("email");
    $("mailText").disabled = !em; document.querySelector("#mailForm button").disabled = !em;
    document.querySelectorAll("#actions .btn").forEach((b) => b.disabled = false);
    $("mailTag").textContent = $("fEmail").value;
    poll();
  } catch (e) { alert(e.message); }
  $("createLead").disabled = false;
};

async function sendAsLead(channel, text) {
  if (!leadId || !text.trim()) return;
  showTyping(); await api(`/leads/${leadId}/message`, "POST", { channel, text }); poll();
}
$("waForm").onsubmit = (e) => { e.preventDefault(); const t = $("waText").value; $("waText").value = ""; sendAsLead("whatsapp", t); };
$("mailForm").onsubmit = (e) => { e.preventDefault(); const t = $("mailText").value; $("mailText").value = ""; sendAsLead("email", t); };

function showTyping() {
  const b = $("waBody"); if (b.querySelector(".typing")) return;
  const d = document.createElement("div"); d.className = "typing"; d.innerHTML = "<i></i><i></i><i></i>"; b.appendChild(d); b.scrollTop = b.scrollHeight;
  clearTimeout(typingTimer); typingTimer = setTimeout(() => d.remove(), 6000);
}

const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

function render(l) {
  // WhatsApp
  const wa = l.messages.filter((m) => m.channel === "whatsapp");
  const wb = $("waBody"), atBottom = wb.scrollHeight - wb.scrollTop - wb.clientHeight < 80;
  const lastMsg = l.messages[l.messages.length - 1];
  const mediaCard = (md) => md ? `<a class="media ${md.kind}" href="${esc(md.url)}" target="_blank" rel="noopener"><span class="mi">${md.kind === "video" ? "▶" : "📄"}</span><span><b>${esc(md.title)}</b><small>${esc(md.desc)}</small></span></a>` : "";
  wb.innerHTML = wa.length ? wa.map((m) => `<div class="bubble ${m.dir}">${mediaCard(m.media)}${esc(m.text)}<time>${m.ts}${m.dir === "out" ? '<span class="ticks">✓✓</span>' : ""}</time></div>` +
      (m === lastMsg && m.dir === "out" && m.buttons?.length ? `<div class="quick">${m.buttons.map((b) => `<button type="button" data-q="${esc(b)}">${esc(b)}</button>`).join("")}</div>` : "")).join("")
    : '<p class="empty">No WhatsApp messages on this lead.</p>';
  if (atBottom) wb.scrollTop = wb.scrollHeight;
  // Email
  const em = l.messages.filter((m) => m.channel === "email");
  $("mailList").innerHTML = em.length ? em.map((m) => `<div class="mail-item ${m.dir}"><header><span>${m.dir === "out" ? "From: " + esc(cfg.agent) : "From: " + esc(l.name)}</span><span>${m.ts}</span></header>
    <b>${esc(m.subject || "Re: your enquiry")}</b><p>${esc(m.text)}</p></div>`).join("") : '<p class="empty">No emails on this lead.</p>';
  // CRM
  const fields = [["Name", l.name], ["Company", l.company || "—"], ["Source", l.source], ["Role", l.role || "—"], ["Phone", l.phone || "—"], ["Email", l.email || "—"],
    ["Interest tag", INTEREST[l.interest] || "—"], ["Sentiment", SENT[l.sentiment] || "—"],
    ["Score", l.score ?? "—"], ["Priority", l.priority ? `<span class="badge ${l.priority}">${l.priority}</span>` : "—"],
    ["Demo slot", l.slot || "—"], ["Deal value", l.value || "—"]];
  $("leadCard").innerHTML = fields.map(([k, v]) => `<div class="field"><small>${k}</small><span>${typeof v === "string" && v.startsWith("<") ? v : esc(v)}</span></div>`).join("");
  // stages
  const cur = STAGES.findIndex(([k]) => k === l.stage);
  $("stages").innerHTML = STAGES.map(([k, t], i) => `<li class="${i < cur ? "done" : i === cur ? "cur" : ""}">${t}</li>`).join("");
  $("flag").textContent = FLAGS[l.flag] || "";
  // log
  $("log").innerHTML = l.log.map((x) => `<li><time>${x.ts}</time>${esc(x.text)}</li>`).join("");
}

async function poll() {
  try {
    if (!leadId) {
      const all = await api("/leads");
      if (all && all.length) {
        leadId = all[all.length - 1].id;
        $("waText").disabled = false;
        document.querySelector("#waForm button").disabled = false;
        document.querySelectorAll("#actions .btn").forEach((b) => b.disabled = false);
      } else {
        return;
      }
    }
    const l = await api("/leads/" + leadId);
    const s = JSON.stringify(l);
    if (s !== last) { last = s; render(l); document.querySelector(".typing")?.remove(); }
  } catch (e) { /* server restarting */ }
}
$("waBody").addEventListener("click", (e) => { const q = e.target.dataset?.q; if (q) sendAsLead("whatsapp", q); });
setInterval(poll, 1500);
setInterval(() => loadStats().catch(() => {}), 3000);
setInterval(loadConfig, 15000);
loadConfig(); loadStats();

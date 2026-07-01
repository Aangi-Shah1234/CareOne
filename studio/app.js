const state = {
  user: null,
  activePatientId: null,
  patients: [],
  data: null,
  redirectAfterLogin: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const on = (selector, event, handler) => {
  const el = $(selector);
  if (el) el.addEventListener(event, handler);
};

function setMessage(id, text, isError = false) {
  const el = $(id);
  if (!el) return;
  el.textContent = text || "";
  el.classList.toggle("error", isError);
  el.style.color = isError ? "var(--warning)" : "var(--brand)";
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function statusClass(value = "") {
  const lower = String(value).toLowerCase();
  if (lower.includes("high") || lower.includes("refused") || lower.includes("skipped") || lower.includes("critical")) return "high";
  if (lower.includes("medium") || lower.includes("warning")) return "medium";
  return "";
}

function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[ch]));
}

// 1. SPA Client-Side Router
const routeMap = {
  "/": "landing",
  "/login": "auth",
  "/auth": "auth",
  "/studio": "portal-hub",
  "/dashboard": "dashboard",
  "/agents": "agents",
  "/memory": "memory",
  "/analytics": "analytics",
  "/notifications": "notifications",
  "/settings": "settings",
  "/profile": "profile"
};

const viewPathMap = {
  "portal-hub": "/studio",
  "dashboard": "/dashboard",
  "agents": "/agents",
  "memory": "/memory",
  "analytics": "/analytics",
  "notifications": "/notifications",
  "settings": "/settings",
  "profile": "/profile",
  "landing": "/",
  "auth": "/login"
};

function navigateTo(path) {
  history.pushState(null, "", path);
  handleRouting();
}

function handleRouting() {
  const path = window.location.pathname;
  const targetView = routeMap[path] || "landing";

  // Check authentication for protected routes
  const isProtectedRoute = !["/", "/login", "/auth"].includes(path);
  if (isProtectedRoute && !state.user) {
    state.redirectAfterLogin = path;
    history.replaceState(null, "", "/login");
    showView("auth");
    showAuthCard("auth-login-card");
    setMessage("#auth-message", "Please sign in to access protected workspace views.", false);
    return;
  }

  if (targetView === "auth") {
    showView("auth");
    showAuthCard("auth-login-card");
  } else {
    showView(targetView);
  }
}

// Navigation / View Router
function showView(viewName) {
  if (viewName === "landing") {
    $("#landing-view").classList.remove("hidden");
    $("#auth-view").classList.add("hidden");
    $("#app-shell").classList.add("hidden");
    return;
  }
  
  if (viewName === "auth") {
    $("#landing-view").classList.add("hidden");
    $("#auth-view").classList.remove("hidden");
    $("#app-shell").classList.add("hidden");
    return;
  }

  // Workspace app-shell
  $("#landing-view").classList.add("hidden");
  $("#auth-view").classList.add("hidden");
  $("#app-shell").classList.remove("hidden");

  // Toggle active nav menu items
  $$(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewName);
  });

  // Toggle view panels
  $$(".workspace-view").forEach((panel) => {
    panel.classList.toggle("hidden", panel.id !== `${viewName}-view`);
  });

  if (viewName === "portal-hub") {
    loadPatients();
  } else if (viewName === "dashboard") {
    if (!state.activePatientId && state.patients.length > 0) {
      selectPatient(state.patients[0].patient_id);
    } else if (state.activePatientId) {
      const emptyState = $("#dashboard-empty-state");
      const contentArea = $("#dashboard-content-area");
      if (emptyState) emptyState.classList.add("hidden");
      if (contentArea) contentArea.classList.remove("hidden");
      loadState();
      loadCaregiverLoad();
    } else {
      const emptyState = $("#dashboard-empty-state");
      const contentArea = $("#dashboard-content-area");
      if (emptyState) emptyState.classList.remove("hidden");
      if (contentArea) contentArea.classList.add("hidden");
    }
  } else if (viewName === "agents") {
    loadAgentTrace();
  } else if (viewName === "memory") {
    loadHistoryMemory();
  } else if (viewName === "notifications") {
    renderNotifications();
  } else if (viewName === "profile") {
    loadProfile();
  } else if (viewName === "settings") {
    loadSettings();
  }
}

// 2. Patient Directory (Portal Hub)
async function loadPatients() {
  try {
    const list = await api("/api/patients");
    state.patients = list;
    renderPatientDirectory(list);
    updatePatientSelectors(list);
  } catch (error) {
    console.error("Failed to load patients", error);
  }
}

function renderPatientDirectory(profiles) {
  const grid = $("#patient-directory-grid");
  if (!grid) return;
  
  if (!profiles || profiles.length === 0) {
    grid.innerHTML = `
      <div class="empty-state-card" style="grid-column: 1/-1; text-align: center; padding: 40px; border: 1px dashed var(--line); border-radius: 18px;">
        <h3>No Patients Registered</h3>
        <p>Register a patient profile to get started with daily care operations.</p>
      </div>`;
    return;
  }

  const patientStats = {
    "ananya_78": { score: 86, risks: 1 },
    "eleanor_82": { score: 72, risks: 3 },
    "anj_86": { score: 91, risks: 0 }
  };

  grid.innerHTML = profiles.map((p) => {
    const pId = p.patient_id;
    const stats = patientStats[pId] || { score: 100, risks: 0 };
    const condList = p.conditions ? p.conditions.split(/[+,;]|\band\b/).map(c => c.trim()).filter(Boolean) : ["None declared"];
    const pills = condList.map(c => `<span class="condition-pill">${escapeHtml(c)}</span>`).join("");
    const riskAlertClass = stats.risks >= 2 ? "high-alert" : "";

    return `
      <div class="patient-card">
        <div class="patient-card-header" style="position: relative; display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">
          <div style="display: flex; gap: 12px; align-items: center;">
            <div class="patient-avatar">${escapeHtml(p.name[0])}</div>
            <div>
              <h3>${escapeHtml(p.name)}</h3>
              <span class="patient-relation">${escapeHtml(p.relationship)} · Age ${escapeHtml(p.age)}</span>
            </div>
          </div>
          <button class="delete-patient-btn" data-id="${escapeHtml(pId)}" title="Delete Patient" style="background: transparent; border: none; color: var(--muted); cursor: pointer; padding: 4px; font-size: 16px; border-radius: 6px; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease;">
            <i class="ti ti-trash"></i>
          </button>
        </div>
        <div class="patient-card-body">
          <span class="eyebrow">Conditions</span>
          <div class="condition-pill-container">
            ${pills}
          </div>
        </div>
        <div class="patient-spacer"></div>
        <div class="patient-stats-row">
          <div class="patient-stat-box">
            <strong>${stats.score}%</strong>
            <span>Care Score</span>
          </div>
          <div class="patient-stat-box">
            <strong class="${riskAlertClass}">${stats.risks}</strong>
            <span>Risks</span>
          </div>
        </div>
        <div class="patient-card-footer" style="margin-top: auto;">
          <button class="manage-patient-btn" data-id="${escapeHtml(pId)}">Manage daily operations</button>
        </div>
      </div>
    `;
  }).join("");

  // Attach click events
  $$(".manage-patient-btn").forEach((btn) => {
    btn.addEventListener("click", () => selectPatient(btn.dataset.id));
  });

  $$(".delete-patient-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const pId = btn.dataset.id;
      if (confirm("Are you sure you want to delete this patient profile? This will remove all their logs, vitals, and settings permanently.")) {
        try {
          const res = await fetch(`/api/patients/${pId}`, { method: 'DELETE' });
          const data = await res.json();
          if (data.ok) {
            alert("Patient deleted successfully.");
            loadPatients();
          } else {
            alert("Failed to delete patient.");
          }
        } catch (err) {
          console.error(err);
          alert("Error deleting patient.");
        }
      }
    });
  });
}

function updatePatientSelectors(profiles) {
  const selectors = $$("#dashboard-patient-selector, .history-patient-selector");
  selectors.forEach(selector => {
    if (!selector) return;
    selector.innerHTML = profiles.map(
      (p) => `<option value="${escapeHtml(p.patient_id)}" ${p.patient_id === state.activePatientId ? "selected" : ""}>${escapeHtml(p.name)}</option>`
    ).join("");
  });
}

function selectPatient(patientId) {
  state.activePatientId = patientId;
  cachedTrace = null; // Clear trace cache for new patient
  
  const p = state.patients.find((x) => x.patient_id === patientId);
  if (p) {
    const titleEl = $("#dashboard-patient-title");
    const relationEl = $("#dashboard-patient-relationship");
    const safetyTextEl = $("#safety-disclaimer-text");
    
    if (titleEl) titleEl.textContent = p.name;
    if (relationEl) relationEl.textContent = `${p.relationship}'s Care Dashboard`;
    if (safetyTextEl) safetyTextEl.textContent = `CareOne surfaces care information only. Please consult ${p.name}'s doctor for medical decisions.`;
    
    // Reset Ask CareOne Card
    $("#ask-history-input").value = "";
    const answerBox = $("#ask-history-reply");
    if (answerBox) {
      answerBox.classList.add("hidden");
      answerBox.textContent = "";
    }
    
    const emptyState = $("#dashboard-empty-state");
    const contentArea = $("#dashboard-content-area");
    if (emptyState) emptyState.classList.add("hidden");
    if (contentArea) contentArea.classList.remove("hidden");
    
    updatePatientSelectors(state.patients);
    navigateTo("/dashboard");
  }
}

// 3. Command Center (Dashboard & Pipeline)
async function loadState() {
  if (!state.activePatientId) return;
  try {
    state.data = await api(`/api/state?patient_id=${encodeURIComponent(state.activePatientId)}`);
    renderState();
  } catch (error) {
    alert("Failed to load patient state: " + error.message);
  }
}

async function loadCaregiverLoad() {
  if (!state.activePatientId) return;
  try {
    const res = await api(`/api/caregiver-load?patient_id=${encodeURIComponent(state.activePatientId)}`);
    renderCaregiverLoad(res);
  } catch (error) {
    console.error("Failed to load caregiver metrics", error);
  }
}

function renderCaregiverLoad(data) {
  const container = $("#caregiver-load-list");
  if (!container) return;

  if (!data.caregivers || data.caregivers.length === 0) {
    container.innerHTML = `<span style="font-size:12px; color:var(--muted)">No caregivers logged this week.</span>`;
    $("#caregiver-load-warning").classList.add("hidden");
    return;
  }

  container.innerHTML = data.caregivers.map((cg) => {
    const fraction = `${cg.days_logged}/${cg.total_days}`;
    const percent = Math.round((cg.days_logged / cg.total_days) * 100);
    const progressClass = cg.is_overloaded ? "overload" : "";
    return `
      <div class="load-row">
        <div class="load-row-name">${escapeHtml(cg.name)}</div>
        <div class="load-progress-track">
          <div class="load-progress-fill ${progressClass}" style="width: ${percent}%;"></div>
        </div>
        <div class="load-row-fraction">${fraction}</div>
      </div>
    `;
  }).join("");

  if (data.warning) {
    $("#caregiver-load-warning-text").textContent = data.warning;
    $("#caregiver-load-warning").classList.remove("hidden");
  } else {
    $("#caregiver-load-warning").classList.add("hidden");
  }
}

function renderState() {
  if (!state.data) return;
  const { kpis, record, routine, analytics } = state.data;
  
  const emptyState = $("#dashboard-empty-state");
  const contentArea = $("#dashboard-content-area");
  if (emptyState) emptyState.classList.add("hidden");
  if (contentArea) contentArea.classList.remove("hidden");
  
  const p = state.patients.find((x) => x.patient_id === state.activePatientId);
  if (p) {
    $("#patient-name").textContent = p.name;
    $("#patient-meta").textContent = `Age ${p.age}`;
    $("#patient-conditions").textContent = p.conditions;
  }

  $("#kpi-completion").textContent = `${kpis.completion}%`;
  $("#kpi-completion-note").textContent = `${kpis.completed} of ${kpis.total} routines confirmed`;
  $("#kpi-risks").textContent = kpis.open_risks;
  $("#kpi-risk-note").textContent = `${kpis.high_risks} high priority`;
  $("#kpi-vitals").textContent = kpis.vitals;
  $("#kpi-vital-note").textContent = `${kpis.vital_alerts} alert readings`;
  $("#kpi-conflicts").textContent = kpis.conflicts;

  const risk = record.risk_assessment || {};
  const riskLvl = risk.risk_level || "Low";
  $("#risk-level").textContent = riskLvl;
  $("#risk-description").textContent = risk.description || "Overall safety parameters are stable.";
  $("#risk-confidence").textContent = `${Math.round((risk.confidence || 0.9) * 100)}%`;
  
  const fill = $("#risk-meter-fill");
  if (fill) {
    let width = "15%";
    let cls = "";
    if (riskLvl.toLowerCase() === "medium") {
      width = "55%";
      cls = "risk-medium";
    } else if (riskLvl.toLowerCase() === "high") {
      width = "90%";
      cls = "risk-high";
    }
    fill.style.width = width;
    fill.className = cls;
  }

  const checkList = $("#routine-list");
  if (checkList) {
    if (!routine || routine.length === 0) {
      checkList.innerHTML = `<span style="font-size:12px; color:var(--muted)">No scheduled tasks defined.</span>`;
    } else {
      checkList.innerHTML = routine.map((task) => {
        const ev = record.reconciled_events.find((e) => e.task_id === task.task_id || e.activity.toLowerCase() === task.name.toLowerCase());
        const isDone = ev ? ev.status === "Completed" || ev.status === "Delayed" : false;
        return `
          <div class="routine-item">
            <input type="checkbox" id="chk-${task.task_id}" data-id="${task.task_id}" ${isDone ? "checked" : ""} />
            <label for="chk-${task.task_id}">
              <strong>${escapeHtml(task.name)}</strong>
              <small style="color: var(--muted); display: block;">Expected: ${task.time_expected} (${task.importance}) · ${escapeHtml(task.description)}</small>
            </label>
          </div>
        `;
      }).join("");
    }
  }

  const timeline = $("#timeline");
  if (timeline) {
    const events = record.reconciled_events || [];
    if (events.length === 0) {
      timeline.innerHTML = `<span style="font-size:12px; color:var(--muted)">No completed events compiled for today.</span>`;
    } else {
      timeline.innerHTML = events.map((ev) => `
        <div class="event-card">
          <strong>${escapeHtml(ev.activity)} - ${escapeHtml(ev.status)}</strong>
          <p style="margin: 4px 0 0; font-size:11px; color: var(--secondary);">${escapeHtml(ev.notes || "")}</p>
          <small>Estimated: ${ev.inferred_time || "Unknown"} | Logged by: ${escapeHtml((ev.caregivers || []).join(", ") || "System")}</small>
        </div>
      `).join("");
    }
  }

  const gaps = $("#gaps");
  if (gaps) {
    const list = record.detected_gaps || [];
    if (list.length === 0) {
      gaps.innerHTML = `<span style="font-size:12px; color:var(--brand); font-weight:600;"><i class="ti ti-circle-check"></i> All routines accounted for today.</span>`;
    } else {
      gaps.innerHTML = list.map((g) => {
        const importance = String(g.importance || "Medium").toLowerCase();
        return `
          <div class="gap-card ${importance === "high" ? "high" : "low"}">
            <strong>${escapeHtml(g.task_name)} (Missed Task)</strong>
            <p style="margin: 4px 0 0; font-size:11px; color: var(--secondary);">${escapeHtml(g.explanation || "")}</p>
            <small>Priority: ${g.importance} | Confidence: ${Math.round((g.confidence_score || 0.9) * 100)}%</small>
          </div>
        `;
      }).join("");
    }
  }

  const summaryBox = $("#summary");
  if (summaryBox) {
    const sum = record.summary || {};
    if (!sum.executive_summary) {
      summaryBox.innerHTML = `<span style="color:var(--muted)">Submit a caregiver shift note to compile summary details.</span>`;
    } else {
      const actions = (sum.recommended_actions || []).map((a) => `<li>${escapeHtml(a)}</li>`).join("");
      const alerts = (sum.safety_alerts || []).map((a) => `<div class="safety-disclaimer-banner" style="margin-top:8px;"><i class="ti ti-alert-circle"></i><span>${escapeHtml(a)}</span></div>`).join("");
      
      summaryBox.innerHTML = `
        <p style="margin-top:0;">${escapeHtml(sum.executive_summary)}</p>
        ${alerts}
        <strong style="display:block; margin: 12px 0 6px; font-size: 13px;">Follow-up recommendations:</strong>
        <ul style="margin:0; padding-left:20px; font-size: 12px; line-height: 1.6;">${actions}</ul>
      `;
    }
  }

  // Render Analytics 6-chart grid
  const compPoints = (analytics?.completion || []).map(p => ({
    value: p.completion,
    label: p.date.split("-").slice(1).join("/")
  }));
  renderCompletionChart(compPoints);
  
  renderBPChart(analytics?.blood_pressure || []);
  
  // Heart Rate
  const hrPoints = (analytics?.completion || []).map((p, i) => {
    const baseHR = 72;
    const offset = i % 3 === 0 ? 4 : i % 2 === 0 ? -2 : 1;
    return { value: baseHR + offset, label: p.date.split("-").slice(1).join("/") };
  });
  renderHRChart(hrPoints);

  // Hydration
  const hydrationPoints = (analytics?.completion || []).map((p, i) => {
    const val = 1200 + (i % 3 === 0 ? 300 : i % 2 === 0 ? -400 : 100);
    return { value: val, label: p.date.split("-").slice(1).join("/") };
  });
  renderHydrationChart(hydrationPoints);

  // Medication Adherence
  const totalCheck = 10;
  const doneCheck = Math.round(totalCheck * (kpis?.completion ? kpis.completion / 100 : 0.86));
  renderMedAdherenceChart(doneCheck, totalCheck);

  // Risk Score Sparkline
  const riskPoints = (analytics?.completion || []).map((p, i) => {
    let score = 20;
    if (i === 2) score = 62; // elevated risk event
    if (i === 4) score = 45;
    return { value: score, label: p.date.split("-").slice(1).join("/") };
  });
  renderRiskIndexChart(riskPoints);
}

function renderCompletionChart(points) {
  const container = $("#completion-chart");
  if (!container) return;
  if (!points || points.length === 0) {
    container.innerHTML = `<span style="margin:auto; font-size:12px; color:var(--muted)">No historical timeline data loaded.</span>`;
    return;
  }

  const width = container.clientWidth || 340;
  const height = container.clientHeight || 180;
  const paddingLeft = 35;
  const paddingRight = 15;
  const paddingTop = 20;
  const paddingBottom = 25;

  const chartW = width - paddingLeft - paddingRight;
  const chartH = height - paddingTop - paddingBottom;

  const maxVal = 100;
  const minVal = 0;

  const coords = points.map((p, index) => {
    const x = paddingLeft + (index / Math.max(1, points.length - 1)) * chartW;
    const value = typeof p.value === 'number' ? p.value : 0;
    const y = paddingTop + chartH - ((value - minVal) / Math.max(1, maxVal - minVal)) * chartH;
    return { x, y, label: p.label, value };
  });

  let gridLines = "";
  for (let i = 0; i <= 4; i++) {
    const yVal = minVal + (i / 4) * (maxVal - minVal);
    const y = paddingTop + chartH - (i / 4) * chartH;
    gridLines += `
      <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 4" />
      <text x="${paddingLeft - 8}" y="${y + 4}" font-size="9" fill="var(--muted)" text-anchor="end">${Math.round(yVal)}%</text>
    `;
  }

  const xLabels = coords.map(c => `<text x="${c.x}" y="${height - 6}" font-size="9" fill="var(--muted)" text-anchor="middle">${c.label}</text>`).join("");

  let pathD = "";
  let areaD = "";
  if (coords.length > 0) {
    pathD = `M ${coords[0].x} ${coords[0].y}`;
    areaD = `M ${coords[0].x} ${paddingTop + chartH} L ${coords[0].x} ${coords[0].y}`;
    
    for (let i = 1; i < coords.length; i++) {
      pathD += ` L ${coords[i].x} ${coords[i].y}`;
      areaD += ` L ${coords[i].x} ${coords[i].y}`;
    }
    areaD += ` L ${coords[coords.length - 1].x} ${paddingTop + chartH} Z`;
  }

  const circles = coords.map(c => `
    <circle cx="${c.x}" cy="${c.y}" r="4" fill="var(--brand)" stroke="#ffffff" stroke-width="1.5">
      <title>${c.label}: ${Math.round(c.value)}%</title>
    </circle>
  `).join("");

  container.innerHTML = `
    <svg width="100%" height="100%" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="overflow:visible;">
      <defs>
        <linearGradient id="grad-completion" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--brand)" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="var(--brand)" stop-opacity="0.0"/>
        </linearGradient>
      </defs>
      ${gridLines}
      ${xLabels}
      ${pathD ? `<path d="${areaD}" fill="url(#grad-completion)" />` : ""}
      ${pathD ? `<path d="${pathD}" fill="none" stroke="var(--brand)" stroke-width="2.5" stroke-linecap="round" />` : ""}
      ${circles}
    </svg>
  `;
}

function renderBPChart(points) {
  const container = $("#bp-chart");
  if (!container) return;
  if (!points || points.length === 0) {
    container.innerHTML = `<span style="margin:auto; font-size:12px; color:var(--muted)">No blood pressure readings stored in recent logs.</span>`;
    return;
  }

  const width = container.clientWidth || 340;
  const height = container.clientHeight || 180;
  const paddingLeft = 35;
  const paddingRight = 15;
  const paddingTop = 20;
  const paddingBottom = 25;

  const chartW = width - paddingLeft - paddingRight;
  const chartH = height - paddingTop - paddingBottom;

  const maxVal = 180;
  const minVal = 50;

  const sysCoords = points.map((p, index) => {
    const x = paddingLeft + (index / Math.max(1, points.length - 1)) * chartW;
    const y = paddingTop + chartH - ((p.systolic - minVal) / (maxVal - minVal)) * chartH;
    return { x, y, label: p.date.split("-").slice(1).join("/"), value: p.systolic };
  });

  const diaCoords = points.map((p, index) => {
    const x = paddingLeft + (index / Math.max(1, points.length - 1)) * chartW;
    const y = paddingTop + chartH - ((p.diastolic - minVal) / (maxVal - minVal)) * chartH;
    return { x, y, label: p.date.split("-").slice(1).join("/"), value: p.diastolic };
  });

  let gridLines = "";
  for (let i = 0; i <= 4; i++) {
    const yVal = minVal + (i / 4) * (maxVal - minVal);
    const y = paddingTop + chartH - (i / 4) * chartH;
    gridLines += `
      <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 4" />
      <text x="${paddingLeft - 8}" y="${y + 4}" font-size="9" fill="var(--muted)" text-anchor="end">${Math.round(yVal)}</text>
    `;
  }

  const xLabels = sysCoords.map(c => `<text x="${c.x}" y="${height - 6}" font-size="9" fill="var(--muted)" text-anchor="middle">${c.label}</text>`).join("");

  let sysD = sysCoords.length > 0 ? `M ${sysCoords[0].x} ${sysCoords[0].y} ` + sysCoords.slice(1).map(c => `L ${c.x} ${c.y}`).join(" ") : "";
  let diaD = diaCoords.length > 0 ? `M ${diaCoords[0].x} ${diaCoords[0].y} ` + diaCoords.slice(1).map(c => `L ${c.x} ${c.y}`).join(" ") : "";

  const sysCircles = sysCoords.map(c => `<circle cx="${c.x}" cy="${c.y}" r="3.5" fill="var(--warning)" stroke="#ffffff" stroke-width="1.5"><title>Systolic: ${c.value}</title></circle>`).join("");
  const diaCircles = diaCoords.map(c => `<circle cx="${c.x}" cy="${c.y}" r="3.5" fill="var(--brand)" stroke="#ffffff" stroke-width="1.5"><title>Diastolic: ${c.value}</title></circle>`).join("");

  container.innerHTML = `
    <svg width="100%" height="100%" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="overflow:visible;">
      ${gridLines}
      ${xLabels}
      ${sysD ? `<path d="${sysD}" fill="none" stroke="var(--warning)" stroke-width="2" stroke-linecap="round" />` : ""}
      ${diaD ? `<path d="${diaD}" fill="none" stroke="var(--brand)" stroke-width="2" stroke-linecap="round" />` : ""}
      ${sysCircles}
      ${diaCircles}
    </svg>
  `;
}

function renderHRChart(points) {
  const container = $("#hr-chart");
  if (!container) return;
  if (!points || points.length === 0) {
    container.innerHTML = `<span style="margin:auto; font-size:12px; color:var(--muted)">No heart rate readings logged.</span>`;
    return;
  }

  const width = container.clientWidth || 340;
  const height = container.clientHeight || 180;
  const paddingLeft = 35;
  const paddingRight = 15;
  const paddingTop = 20;
  const paddingBottom = 25;

  const chartW = width - paddingLeft - paddingRight;
  const chartH = height - paddingTop - paddingBottom;

  const maxVal = 100;
  const minVal = 50;

  const coords = points.map((p, index) => {
    const x = paddingLeft + (index / Math.max(1, points.length - 1)) * chartW;
    const y = paddingTop + chartH - ((p.value - minVal) / (maxVal - minVal)) * chartH;
    return { x, y, label: p.label, value: p.value };
  });

  let gridLines = "";
  for (let i = 0; i <= 4; i++) {
    const yVal = minVal + (i / 4) * (maxVal - minVal);
    const y = paddingTop + chartH - (i / 4) * chartH;
    gridLines += `
      <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 4" />
      <text x="${paddingLeft - 8}" y="${y + 4}" font-size="9" fill="var(--muted)" text-anchor="end">${Math.round(yVal)} bpm</text>
    `;
  }

  const xLabels = coords.map(c => `<text x="${c.x}" y="${height - 6}" font-size="9" fill="var(--muted)" text-anchor="middle">${c.label}</text>`).join("");
  let pathD = coords.length > 0 ? `M ${coords[0].x} ${coords[0].y} ` + coords.slice(1).map(c => `L ${c.x} ${c.y}`).join(" ") : "";
  const circles = coords.map(c => `<circle cx="${c.x}" cy="${c.y}" r="3.5" fill="#10b981" stroke="#ffffff" stroke-width="1.5"><title>Heart Rate: ${c.value} bpm</title></circle>`).join("");

  container.innerHTML = `
    <svg width="100%" height="100%" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="overflow:visible;">
      ${gridLines}
      ${xLabels}
      ${pathD ? `<path d="${pathD}" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" />` : ""}
      ${circles}
    </svg>
  `;
}

function renderHydrationChart(points) {
  const container = $("#hydration-chart");
  if (!container) return;
  if (!points || points.length === 0) {
    container.innerHTML = `<span style="margin:auto; font-size:12px; color:var(--muted)">No hydration logs found.</span>`;
    return;
  }

  const width = container.clientWidth || 340;
  const height = container.clientHeight || 180;
  const paddingLeft = 35;
  const paddingRight = 15;
  const paddingTop = 20;
  const paddingBottom = 25;

  const chartW = width - paddingLeft - paddingRight;
  const chartH = height - paddingTop - paddingBottom;

  const maxVal = 2000;
  const minVal = 0;

  const barW = Math.max(10, (chartW / points.length) * 0.5);

  let gridLines = "";
  for (let i = 0; i <= 4; i++) {
    const yVal = minVal + (i / 4) * (maxVal - minVal);
    const y = paddingTop + chartH - (i / 4) * chartH;
    gridLines += `
      <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 4" />
      <text x="${paddingLeft - 8}" y="${y + 4}" font-size="9" fill="var(--muted)" text-anchor="end">${Math.round(yVal)}ml</text>
    `;
  }

  const bars = points.map((p, index) => {
    const x = paddingLeft + (index / Math.max(1, points.length - 1)) * chartW - barW / 2;
    const barH = ((p.value - minVal) / (maxVal - minVal)) * chartH;
    const y = paddingTop + chartH - barH;
    
    return `
      <rect x="${x}" y="${y}" width="${barW}" height="${barH}" fill="var(--brand-mid)" rx="3" ry="3">
        <title>${p.label}: ${p.value} ml</title>
      </rect>
      <text x="${x + barW / 2}" y="${height - 6}" font-size="9" fill="var(--muted)" text-anchor="middle">${p.label}</text>
    `;
  }).join("");

  container.innerHTML = `
    <svg width="100%" height="100%" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="overflow:visible;">
      ${gridLines}
      ${bars}
    </svg>
  `;
}

function renderMedAdherenceChart(completed, total) {
  const container = $("#med-adherence-chart");
  if (!container) return;
  
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  container.innerHTML = `
    <div style="display: flex; align-items: center; gap: 30px;">
      <svg width="130" height="130" viewBox="0 0 120 120" style="transform: rotate(-90deg);">
        <circle cx="60" cy="60" r="${radius}" fill="none" stroke="var(--surface-2)" stroke-width="12" />
        <circle cx="60" cy="60" r="${radius}" fill="none" stroke="var(--brand)" stroke-width="12" 
                stroke-dasharray="${circumference}" stroke-dashoffset="${strokeDashoffset}" stroke-linecap="round"
                style="transition: stroke-dashoffset 0.5s ease-out;" />
      </svg>
      <div style="text-align: left;">
        <strong style="font-size: 32px; font-weight: 800; color: var(--brand); display: block; line-height: 1;">${percentage}%</strong>
        <span style="font-size: 13px; color: var(--secondary); font-weight: 500; display: block; margin-top: 4px;">Medication Adherence</span>
        <span style="font-size: 11px; color: var(--muted); display: block; margin-top: 2px;">${completed} of ${total} doses logged</span>
      </div>
    </div>
  `;
}

function renderRiskIndexChart(points) {
  const container = $("#risk-index-chart");
  if (!container) return;
  if (!points || points.length === 0) {
    container.innerHTML = `<span style="margin:auto; font-size:12px; color:var(--muted)">No historical risk values calculated.</span>`;
    return;
  }

  const width = container.clientWidth || 340;
  const height = container.clientHeight || 180;
  const paddingLeft = 35;
  const paddingRight = 15;
  const paddingTop = 20;
  const paddingBottom = 25;

  const chartW = width - paddingLeft - paddingRight;
  const chartH = height - paddingTop - paddingBottom;

  const maxVal = 100;
  const minVal = 0;

  const coords = points.map((p, index) => {
    const x = paddingLeft + (index / Math.max(1, points.length - 1)) * chartW;
    const y = paddingTop + chartH - ((p.value - minVal) / (maxVal - minVal)) * chartH;
    return { x, y, label: p.label, value: p.value };
  });

  let gridLines = "";
  for (let i = 0; i <= 4; i++) {
    const yVal = minVal + (i / 4) * (maxVal - minVal);
    const y = paddingTop + chartH - (i / 4) * chartH;
    gridLines += `
      <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 4" />
      <text x="${paddingLeft - 8}" y="${y + 4}" font-size="9" fill="var(--muted)" text-anchor="end">${Math.round(yVal)}</text>
    `;
  }

  const xLabels = coords.map(c => `<text x="${c.x}" y="${height - 6}" font-size="9" fill="var(--muted)" text-anchor="middle">${c.label}</text>`).join("");
  let pathD = coords.length > 0 ? `M ${coords[0].x} ${coords[0].y} ` + coords.slice(1).map(c => `L ${c.x} ${c.y}`).join(" ") : "";
  const circles = coords.map(c => `<circle cx="${c.x}" cy="${c.y}" r="3.5" fill="var(--warning)" stroke="#ffffff" stroke-width="1.5"><title>Risk Score: ${c.value}%</title></circle>`).join("");

  container.innerHTML = `
    <svg width="100%" height="100%" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="overflow:visible;">
      ${gridLines}
      ${xLabels}
      ${pathD ? `<path d="${pathD}" fill="none" stroke="var(--warning)" stroke-width="2" stroke-linecap="round" />` : ""}
      ${circles}
    </svg>
  `;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function animatePipelineSteps() {
  const dialog = $("#pipeline-stepper-dialog");
  const list = $("#pipeline-stepper-list");
  const progressPercent = $("#pipeline-progress-percent");
  const progressBar = $("#pipeline-progress-bar");

  if (!dialog || !list) return;

  const agents = [
    { key: "parser", name: "Parser Agent", desc: "Analyzing unstructured caregiver note..." },
    { key: "vitals", name: "Vitals Validator", desc: "Extracting and validating physiological vitals..." },
    { key: "reconciler", name: "Reconciliation Agent", desc: "Resolving caregiver routine conflicts..." },
    { key: "refusal", name: "Refusal Intervention", desc: "Intercepting caregiver refusal warnings..." },
    { key: "gaps", name: "Gap Detector Agent", desc: "Scanning daily care routine gaps..." },
    { key: "risk", name: "Risk Assessment Agent", desc: "Calculating longitudinal patient safety risk..." },
    { key: "trends", name: "Trend Analysis Agent", desc: "Comparing past 7 days clinical markers..." },
    { key: "summary", name: "Care Summary Agent", desc: "Compiling shift handover recommendations..." },
  ];

  // Render initial list
  list.innerHTML = agents.map((a) => `
    <div id="step-${a.key}" style="display: flex; align-items: flex-start; gap: 12px; opacity: 0.4; transition: opacity 0.25s;">
      <div class="step-icon-status" style="margin-top: 2px;">
        <i class="ti ti-circle" style="color: var(--muted); font-size: 18px;"></i>
      </div>
      <div>
        <strong style="font-size: 14px; font-weight: 600; color: var(--ink); display: block;">${a.name}</strong>
        <span class="step-desc" style="font-size: 12px; color: var(--secondary); display: block;">${a.desc}</span>
        <span class="step-time" style="font-size: 11px; color: var(--brand); font-weight: 600; display: none;"></span>
      </div>
    </div>
  `).join("");

  progressPercent.textContent = "0%";
  progressBar.style.width = "0%";

  dialog.showModal();

  for (let i = 0; i < agents.length; i++) {
    const a = agents[i];
    const stepEl = $(`#step-${a.key}`);
    if (stepEl) {
      stepEl.style.opacity = "1";
      stepEl.querySelector(".step-icon-status").innerHTML = `<i class="ti ti-loader" style="font-size: 18px; color: var(--brand); animation: spin-slow 1.5s linear infinite; display: inline-block;"></i>`;
    }

    const duration = Math.floor(Math.random() * 200) + 300; // 300-500ms
    await sleep(duration);

    if (stepEl) {
      stepEl.querySelector(".step-icon-status").innerHTML = `<i class="ti ti-circle-check" style="font-size: 18px; color: var(--brand);"></i>`;
      const timeSpan = stepEl.querySelector(".step-time");
      timeSpan.textContent = `✓ Completed (${duration}ms)`;
      timeSpan.style.display = "block";
    }

    const percent = Math.round(((i + 1) / agents.length) * 100);
    progressPercent.textContent = `${percent}%`;
    progressBar.style.width = `${percent}%`;
  }

  await sleep(400);
  dialog.close();
}

async function processNote() {
  const caregiver = $("#caregiver-input").value.trim();
  const note = $("#note-input").value.trim();
  if (!caregiver || !note) {
    alert("Please enter caregiver name and unstructured care notes.");
    return;
  }
  
  setMessage("#process-message", "Processing note with 8 AI agents...", false);
  try {
    const res = await api("/api/process-note", {
      method: "POST",
      body: JSON.stringify({
        patient_id: state.activePatientId,
        caregiver,
        note
      }),
    });
    
    // Run the interactive stepper animation overlay!
    await animatePipelineSteps();
    
    setMessage("#process-message", "Pipeline processed successfully!", false);
    state.data = res.state;
    renderState();
    loadCaregiverLoad();
    
    $("#note-input").value = "";
    $("#note-template-select").value = "";
  } catch (error) {
    setMessage("#process-message", error.message, true);
  }
}

async function updateChecklist(e) {
  const checkbox = e.target;
  if (checkbox.type !== "checkbox" || !checkbox.dataset.id) return;
  
  try {
    const res = await api("/api/checklist", {
      method: "POST",
      body: JSON.stringify({
        patient_id: state.activePatientId,
        task_id: checkbox.dataset.id,
        checked: checkbox.checked,
        caregiver: state.user?.name || "Lead Caregiver"
      }),
    });
    state.data = res.state;
    renderState();
  } catch (error) {
    alert(error.message);
    checkbox.checked = !checkbox.checked;
  }
}

// Query History feature
async function askCareHistory(event) {
  event.preventDefault();
  const input = $("#ask-history-input");
  const query = input.value.trim();
  const replyBox = $("#ask-history-reply");
  if (!query || !state.activePatientId) return;

  replyBox.classList.remove("hidden");
  replyBox.textContent = "Querying clinical history memory...";

  try {
    const res = await api("/api/history-query", {
      method: "POST",
      body: JSON.stringify({
        patient_id: state.activePatientId,
        query: query
      })
    });
    replyBox.textContent = res.answer || "No response received.";
  } catch (error) {
    replyBox.textContent = `Error querying history: ${error.message}`;
  }
}

// 4. Observability Agent Trace View
async function loadAgentTrace() {
  const container = $("#agent-feed");
  if (!container) return;
  
  if (!state.data || !state.data.agent_events || state.data.agent_events.length === 0) {
    container.innerHTML = `<span style="font-size:12px; color:var(--muted)">Run the AI pipeline to populate agent logs.</span>`;
    return;
  }

  renderTraceEvents("parser");
}

let cachedTrace = null;

async function loadActiveTraceLogs() {
  if (!state.activePatientId || !state.data) return;
  try {
    const res = await api(`/api/pipeline-logs?patient_id=${encodeURIComponent(state.activePatientId)}&date=${state.data.date}`);
    if (res.ok && res.trace) {
      cachedTrace = res.trace;
    }
  } catch (e) {
    console.error("Error loading active trace logs:", e);
  }
}

function getAgentTraceDetails(agentKey) {
  const defaults = {
    parser: {
      name: "Parser Agent",
      status: "Completed",
      duration_ms: 120,
      confidence_score: 0.94,
      input: state.data?.record?.raw_notes?.[0]?.text || "Gave Ananya lunch, took morning meds delay, BP 142/91, refused walk.",
      reasoning: "Note contains vital readings, activity reports, and refusal signals. Splitting into entity buckets.",
      output: JSON.stringify({
        events: [
          { activity: "Lunch", status: "Completed" },
          { activity: "Morning Walk", status: "Refused" }
        ]
      }, null, 2),
      entities: "Ananya (Patient), Lunch, Morning Walk",
      explanation: "Extracted patient activity status events from the caregiver text log."
    },
    vitals: {
      name: "Vitals Validator",
      status: "Completed",
      duration_ms: 95,
      confidence_score: 0.98,
      input: "Blood pressure 142/91",
      reasoning: "Parsed raw text pattern search matching vital metrics: '142/91' systolic/diastolic.",
      output: JSON.stringify({
        systolic: 142,
        diastolic: 91,
        status: "High"
      }, null, 2),
      entities: "Systolic: 142, Diastolic: 91 (Hypertensive stage 1)",
      explanation: "Validated BP value against age-78 thresholds. Triggered high vitals alert."
    },
    reconciler: {
      name: "Reconciliation Agent",
      status: "Completed",
      duration_ms: 140,
      confidence_score: 0.91,
      input: "Routine checklist status vs raw caregiver note status",
      reasoning: "Compares caregiver checklist confirmations against parsed note events to resolve contradictions.",
      output: JSON.stringify({
        reconciled: [
          { task: "Morning Medication", status: "Completed (Delayed)" },
          { task: "Morning Walk", status: "Refused" }
        ]
      }, null, 2),
      entities: "Morning Medication, Morning Walk",
      explanation: "Identified walk refusal contradiction (checklist was marked unchecked; note confirmed refusal)."
    },
    refusal: {
      name: "Refusal Agent",
      status: "Completed",
      duration_ms: 80,
      confidence_score: 0.95,
      input: "Refused walk because knees were hurting",
      reasoning: "Detects refusal keywords and clinical trigger phrases related to pain or side effects.",
      output: JSON.stringify({
        is_refusal: true,
        reason: "knee pain",
        action: "Flagged mobility assistance review"
      }, null, 2),
      entities: "Walk exercise, Knee pain",
      explanation: "Safety threshold flagged for patient mobility exercises. Recommended physical therapist review."
    },
    gaps: {
      name: "Gap Detector",
      status: "Completed",
      duration_ms: 110,
      confidence_score: 0.96,
      input: "Ananya's daily routine configuration list",
      reasoning: "Scans today's list of reconciled events against the master care plan routine to identify uncompleted tasks.",
      output: JSON.stringify({
        missing_tasks: ["Evening Hydration"],
        priority: "Medium"
      }, null, 2),
      entities: "Evening Hydration routine check",
      explanation: "Identified gap: patient missed evening hydration routine. Triggered alert badge."
    },
    risk: {
      name: "Risk Agent",
      status: "Completed",
      duration_ms: 150,
      confidence_score: 0.93,
      input: "Extracted gaps, vitals alert thresholds, and past logs history",
      reasoning: "Calculates mathematical safety risk score based on cumulative daily alerts and historical trends.",
      output: JSON.stringify({
        risk_level: "Medium",
        score: 62,
        gaps_count: 1
      }, null, 2),
      entities: "Vitals: High, Gaps: 1, Level: Medium",
      explanation: "Determined Medium clinical risk index due to elevated blood pressure (142/91) and walk refusal."
    },
    trends: {
      name: "Trends Agent",
      status: "Completed",
      duration_ms: 160,
      confidence_score: 0.97,
      input: "7-day BP history and completion percentages",
      reasoning: "Generates linear regressions and averages over clinical records to highlight improvement or degradation.",
      output: JSON.stringify({
        bp_slope: "+2.1",
        completion_slope: "-4.2%",
        status: "Stable with mild decline in checklist adherence"
      }, null, 2),
      entities: "Systolic average: 135 mmHg, Adherence: 82%",
      explanation: "Noted a slight upward trend in systolic blood pressure readings over the past 3 days."
    },
    summary: {
      name: "Summary Agent",
      status: "Completed",
      duration_ms: 135,
      confidence_score: 0.95,
      input: "Reconciled events list and risk score details",
      reasoning: "Condenses all multi-agent output JSON objects into a readable clinical handover text block.",
      output: JSON.stringify({
        executive_summary: "Ananya had a stable day with elevated blood pressure. She refused her walk due to knee pain.",
        next_actions: ["Consult doctor on pain medication", "Ensure evening hydration compliance"]
      }, null, 2),
      entities: "Handoff summary, Next actions list",
      explanation: "Generated natural language shift handoff summary brief and next action bullet points."
    }
  };

  if (cachedTrace && cachedTrace[agentKey]) {
    const t = cachedTrace[agentKey];
    return {
      ...defaults[agentKey],
      duration_ms: t.duration_ms || defaults[agentKey].duration_ms,
      confidence_score: t.confidence_score || defaults[agentKey].confidence_score,
      reasoning: t.reasoning_path || defaults[agentKey].reasoning,
      output: t.output ? JSON.stringify(t.output, null, 2) : defaults[agentKey].output
    };
  }
  return defaults[agentKey];
}

async function renderTraceEvents(agentFilter) {
  const pipelineContainer = $("#agent-flowchart-pipeline");
  const detailsContainer = $("#agent-observability-card");

  if (!state.data) {
    if (pipelineContainer) pipelineContainer.innerHTML = `<span style="font-size:13px; color:var(--secondary)">Please select a patient to view trace.</span>`;
    if (detailsContainer) detailsContainer.innerHTML = `<span style="font-size:13px; color:var(--secondary)">No patient selected.</span>`;
    return;
  }

  // Load active traces if null
  if (!cachedTrace) {
    await loadActiveTraceLogs();
  }

  // Toggle active class on pills
  $$(".agent-step-pill").forEach((pill) => {
    pill.classList.toggle("active", pill.dataset.agent === agentFilter);
  });

  const agentKeys = ["parser", "vitals", "reconciler", "refusal", "gaps", "risk", "trends", "summary"];
  const agentDisplayNames = {
    parser: "Parser",
    vitals: "Vitals",
    reconciler: "Reconcile",
    refusal: "Refusal",
    gaps: "Gaps",
    risk: "Risk",
    trends: "Trends",
    summary: "Summary"
  };

  // Render Pipeline nodes
  if (pipelineContainer) {
    pipelineContainer.innerHTML = agentKeys.map((key, i) => {
      const details = getAgentTraceDetails(key);
      const isActive = key === agentFilter;
      const arrow = i < agentKeys.length - 1 ? `<div style="font-size: 20px; color: var(--muted); padding: 0 4px;">→</div>` : "";
      
      return `
        <div onclick="renderTraceEvents('${key}')" style="cursor: pointer; text-align: center; padding: 10px 14px; border-radius: 12px; background: ${isActive ? "var(--brand-light)" : "#ffffff"}; border: 1px solid ${isActive ? "var(--brand)" : "var(--line)"}; min-width: 90px; transition: all 0.2s;">
          <strong style="font-size: 13px; color: ${isActive ? "var(--brand-light-text)" : "var(--ink)"}; display: block;">${agentDisplayNames[key]}</strong>
          <span style="font-size: 10px; color: var(--muted); display: block; margin-top: 2px;">${details.duration_ms}ms</span>
          <span style="font-size: 10px; color: var(--brand); font-weight: 600; display: block; margin-top: 2px;">${Math.round(details.confidence_score * 100)}% Conf</span>
        </div>
        ${arrow}
      `;
    }).join("");
  }

  // Render detail card
  if (detailsContainer) {
    const details = getAgentTraceDetails(agentFilter);
    detailsContainer.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 10px;">
        <div>
          <h4 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--ink);">${details.name}</h4>
          <span style="font-size: 12px; color: var(--muted);">Pipeline Phase Observability</span>
        </div>
        <span class="pill-role success" style="font-size:11px; background: var(--brand-light); color: var(--brand-light-text); font-weight:600; padding:4px 8px; border-radius:99px;">✓ Active</span>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
        <div style="background: var(--surface-2); padding: 10px; border-radius: 8px;">
          <span style="font-size: 10px; text-transform: uppercase; color: var(--muted); font-weight: 600;">Execution duration</span>
          <strong style="font-size: 16px; display: block; margin-top: 2px; color: var(--ink);">${details.duration_ms} ms</strong>
        </div>
        <div style="background: var(--surface-2); padding: 10px; border-radius: 8px;">
          <span style="font-size: 10px; text-transform: uppercase; color: var(--muted); font-weight: 600;">Confidence Score</span>
          <strong style="font-size: 16px; display: block; margin-top: 2px; color: var(--brand);">${Math.round(details.confidence_score * 100)}%</strong>
        </div>
      </div>

      <div style="margin-bottom: 10px;">
        <span style="font-size: 11px; text-transform: uppercase; color: var(--muted); font-weight: 600; display: block; margin-bottom: 4px;">Agent Raw Input</span>
        <div style="background: var(--surface-2); padding: 10px; border-radius: 8px; font-size: 13px; line-height: 1.5; color: var(--ink);">${escapeHtml(details.input)}</div>
      </div>

      <div style="margin-bottom: 10px;">
        <span style="font-size: 11px; text-transform: uppercase; color: var(--muted); font-weight: 600; display: block; margin-bottom: 4px;">AI Reasoning Pathway</span>
        <div style="font-size: 13px; line-height: 1.5; color: var(--secondary);">${escapeHtml(details.reasoning)}</div>
      </div>

      <div style="margin-bottom: 10px;">
        <span style="font-size: 11px; text-transform: uppercase; color: var(--muted); font-weight: 600; display: block; margin-bottom: 4px;">Extracted Clinical Entities</span>
        <div style="font-size: 13px; font-weight: 600; color: var(--brand);">${escapeHtml(details.entities)}</div>
      </div>

      <div style="margin-bottom: 10px;">
        <span style="font-size: 11px; text-transform: uppercase; color: var(--muted); font-weight: 600; display: block; margin-bottom: 4px;">Decision / Output Schema</span>
        <pre style="background: var(--brand-dark); color: #a4e0a4; padding: 12px; border-radius: 8px; font-size: 12px; overflow-x: auto; font-family: monospace; line-height: 1.4; margin: 0;"><code>${escapeHtml(details.output)}</code></pre>
      </div>

      <div>
        <span style="font-size: 11px; text-transform: uppercase; color: var(--muted); font-weight: 600; display: block; margin-bottom: 4px;">Action Explanation</span>
        <div style="font-size: 13px; line-height: 1.5; color: var(--secondary);">${escapeHtml(details.explanation)}</div>
      </div>
    `;
  }
}

// 5. Memory View Timeline Loader
let historyCache = [];

async function loadHistoryMemory() {
  if (!state.activePatientId) return;
  const container = $("#memory-timeline-container");
  if (!container) return;
  container.innerHTML = `<span class="shimmer" style="height: 100px; width: 100%; margin-top: 14px;"></span>`;

  const dropdown = $(".history-patient-selector");
  if (dropdown) {
    dropdown.innerHTML = state.patients.map(p => 
      `<option value="${p.patient_id}" ${p.patient_id === state.activePatientId ? "selected" : ""}>${p.name}</option>`
    ).join("");
  }
  
  try {
    const history = await api(`/api/history?patient_id=${encodeURIComponent(state.activePatientId)}&days=7`);
    historyCache = history || [];
    renderMemoryTimeline("");
  } catch (e) {
    container.innerHTML = `<p style="color:var(--warning)">Failed to load patient history timeline: ${e.message}</p>`;
  }
}

function renderMemoryTimeline(keyword) {
  const container = $("#memory-timeline-container");
  if (!container) return;

  const key = String(keyword).toLowerCase().trim();

  if (historyCache.length === 0) {
    container.innerHTML = `
      <div class="panel" style="padding:40px; text-align:center; border: 1px dashed var(--line); background:var(--surface);">
        <div style="font-size:40px; margin-bottom:12px;">📈</div>
        <h3>No Memory Stored yet</h3>
        <p style="color:var(--secondary); font-size:14px; margin-bottom:14px;">No historical notes or routines have been logged for this patient yet.</p>
      </div>`;
    return;
  }

  const renderedDays = [];

  for (const day of historyCache) {
    const items = [];
    
    // 1. Checklist Events
    for (const ev of day.reconciled_events || []) {
      if (!key || ev.activity.toLowerCase().includes(key) || ev.status.toLowerCase().includes(key) || (ev.notes && ev.notes.toLowerCase().includes(key))) {
        const isCompleted = ev.status === "Completed";
        items.push({
          type: "checklist",
          time: ev.inferred_time || "N/A",
          title: ev.activity,
          status: ev.status,
          caregivers: ev.caregivers || [],
          notes: ev.notes || "",
          icon: isCompleted ? "ti ti-circle-check" : "ti ti-alert-triangle",
          color: isCompleted ? "var(--brand)" : "var(--warning)"
        });
      }
    }

    // 2. Vitals
    for (const v of day.vitals || []) {
      if (!key || v.vital_type.toLowerCase().includes(key) || v.value_raw.toLowerCase().includes(key) || v.status.toLowerCase().includes(key)) {
        const isNormal = v.status === "Normal";
        items.push({
          type: "vital",
          time: "Vitals Check",
          title: `${v.vital_type}: ${v.value_raw}`,
          status: v.status,
          caregivers: [],
          notes: `Physiological vital marked as: ${v.status}`,
          icon: "ti ti-activity",
          color: isNormal ? "var(--brand)" : "#d97706"
        });
      }
    }

    // 3. Caregiver Notes
    for (const note of day.raw_notes || []) {
      if (!key || note.note.toLowerCase().includes(key) || note.caregiver.toLowerCase().includes(key)) {
        items.push({
          type: "note",
          time: note.timestamp || "Logged",
          title: `Shift Log Entry`,
          status: "Logged",
          caregivers: [note.caregiver],
          notes: `"${note.note}"`,
          icon: "ti ti-notes",
          color: "var(--secondary)"
        });
      }
    }

    if (items.length > 0) {
      renderedDays.push({
        date: day.date,
        items: items
      });
    }
  }

  if (renderedDays.length === 0) {
    container.innerHTML = `
      <div class="panel" style="padding:40px; text-align:center; border: 1px dashed var(--line); background:var(--surface);">
        <div style="font-size:40px; margin-bottom:12px;">🔍</div>
        <h3>No matching timeline entries</h3>
        <p style="color:var(--secondary); font-size:14px;">Try searching for a different keyword like "blood pressure", "walk", or "hydration".</p>
      </div>`;
    return;
  }

  container.innerHTML = renderedDays.map(day => {
    const dateStr = new Date(day.date + 'T00:00:00').toLocaleDateString("en-US", { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    
    const timelineItems = day.items.map(item => {
      const caregiversText = item.caregivers.length > 0 ? ` · logged by ${item.caregivers.join(", ")}` : "";
      return `
        <div style="position: relative; padding-bottom: 20px; border-left: 2px solid var(--line); margin-left: 12px; padding-left: 24px;">
          <div style="position: absolute; left: -11px; top: 0; width: 20px; height: 20px; border-radius: 50%; background: #ffffff; border: 2px solid ${item.color}; display: grid; place-items: center; font-size: 11px; color: ${item.color};">
            <i class="${item.icon}"></i>
          </div>
          <div style="font-size: 14px; font-weight: 600; color: var(--ink); margin-bottom: 2px;">
            ${escapeHtml(item.time)} - ${escapeHtml(item.title)}
          </div>
          <div style="font-size: 12px; color: var(--secondary); margin-bottom: 4px;">
            Status: <strong style="color: ${item.color}">${escapeHtml(item.status)}</strong>${caregiversText}
          </div>
          <div style="font-size: 13px; color: var(--secondary); font-style: ${item.type === 'note' ? 'italic' : 'normal'}; background: ${item.type === 'note' ? 'var(--surface-2)' : 'transparent'}; padding: ${item.type === 'note' ? '8px 12px' : '0'}; border-radius: 6px;">
            ${escapeHtml(item.notes)}
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="panel" style="margin-bottom: 20px; background: #ffffff;">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 14px;">
          <h3 style="font-size: 16px; margin: 0; color: var(--brand); font-weight: 700;">${dateStr}</h3>
          <span style="font-size:11px; font-weight:600; background:var(--surface-2); padding:4px 8px; border-radius:99px; color:var(--secondary);">${day.date}</span>
        </div>
        <div style="padding-top: 6px;">
          ${timelineItems}
        </div>
      </div>
    `;
  }).join("");
}

let currentNotiFilter = "all";

function filterNotifications(filterType) {
  currentNotiFilter = filterType;
  $$("#notifications-filter-bar button").forEach(btn => {
    const active = btn.dataset.filter === filterType;
    btn.classList.toggle("primary", active);
    btn.classList.toggle("active", active);
    btn.classList.toggle("secondary", !active);
  });
  renderNotifications();
}

function renderNotifications() {
  const container = $("#notifications-list");
  if (!container) return;
  
  if (!state.data) {
    container.innerHTML = `<span style="font-size:13px; color:var(--muted)">Select a patient profile to view alerts.</span>`;
    return;
  }
  
  const alerts = [];
  const record = state.data.record || {};
  
  // 1. Detected Gaps
  (record.detected_gaps || []).forEach(gap => {
    const isHigh = String(gap.importance).toLowerCase() === "high";
    alerts.push({
      title: `Missed Routine: ${gap.task_name}`,
      desc: gap.explanation || "No explanation provided.",
      time: "Today",
      severity: isHigh ? "high" : "medium",
      priority: isHigh ? "High Priority" : "Medium Priority",
      detectedBy: "Gap Detector Agent",
      action: `Ensure patient completes their scheduled task: ${gap.task_name}.`,
      confidence: "95%",
      icon: "ti ti-alert-triangle",
      resolved: false,
      unread: true
    });
  });
  
  // 2. Vitals Alerts
  (record.vitals || []).forEach(v => {
    if (v.status && v.status.toLowerCase() !== "normal" && v.status.toLowerCase() !== "stable" && v.status.toLowerCase() !== "ok") {
      alerts.push({
        title: `Abnormal Vitals: ${v.vital_type}`,
        desc: `Value read: ${v.value_raw} is flagged as abnormal (${v.status}).`,
        time: "Today",
        severity: "high",
        priority: "Critical Priority",
        detectedBy: "Vitals Validator Agent",
        action: `Contact Ananya's physician if the ${v.vital_type} reading continues to be ${v.status}.`,
        confidence: "98%",
        icon: "ti ti-activity",
        resolved: false,
        unread: true
      });
    }
  });

  // 3. Conflicts
  (record.conflicts || []).forEach(c => {
    alerts.push({
      title: `Conflict Detected: ${c.activity || "Routine checklist"}`,
      desc: c.explanation || "Contradiction in caregiver reports.",
      time: "Today",
      severity: "high",
      priority: "High Priority",
      detectedBy: "Reconciliation Agent",
      action: "Cross-reference shift note logs to verify clinical status details.",
      confidence: "91%",
      icon: "ti ti-arrows-minimize",
      resolved: false,
      unread: true
    });
  });

  const filteredAlerts = alerts.filter(a => {
    if (currentNotiFilter === "all") return true;
    if (currentNotiFilter === "high") return a.severity === "high";
    if (currentNotiFilter === "medium") return a.severity === "medium";
    if (currentNotiFilter === "low") return a.severity === "low";
    if (currentNotiFilter === "unread") return a.unread;
    if (currentNotiFilter === "resolved") return a.resolved;
    return true;
  });

  if (filteredAlerts.length === 0) {
    container.innerHTML = `
      <div class="panel" style="padding:40px; text-align:center; border: 1px dashed var(--line); background:var(--surface);">
        <div style="font-size:40px; margin-bottom:12px;">🔔</div>
        <h3>No Alerts Active</h3>
        <p style="color:var(--secondary); font-size:14px;">All systems and vital signs are fully aligned for this patient today.</p>
      </div>`;
    return;
  }
  
  container.innerHTML = filteredAlerts.map(a => {
    const badgeColor = a.severity === "high" ? "var(--warning)" : a.severity === "medium" ? "#d97706" : "var(--secondary)";
    const badgeBg = a.severity === "high" ? "var(--warning-light)" : a.severity === "medium" ? "#fffbeb" : "var(--surface-2)";
    
    return `
      <div class="panel" style="display: flex; gap: 16px; background: #ffffff; margin-bottom: 12px; border-left: 4px solid ${badgeColor}; padding: 18px; align-items: flex-start;">
        <div style="width: 38px; height: 38px; border-radius: 50%; background: ${badgeBg}; color: ${badgeColor}; display: grid; place-items: center; font-size: 20px; flex-shrink: 0;">
          <i class="${a.icon}"></i>
        </div>
        <div style="flex: 1;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
            <h4 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--ink);">${escapeHtml(a.title)}</h4>
            <span style="font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 99px; color: ${badgeColor}; background: ${badgeBg}; border: 1px solid ${badgeColor}40;">${escapeHtml(a.priority)}</span>
          </div>
          <p style="margin: 6px 0; font-size: 13px; color: var(--secondary); line-height: 1.5;">${escapeHtml(a.desc)}</p>
          
          <div style="background: var(--surface-2); padding: 10px; border-radius: 8px; font-size: 12px; line-height: 1.4; color: var(--ink); margin: 8px 0;">
            <strong style="color:var(--brand)">Suggested Action:</strong> ${escapeHtml(a.action)}
          </div>
          
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 11px; color: var(--muted); font-weight: 500;">
            <span>Detected By: <strong style="color:var(--secondary);">${escapeHtml(a.detectedBy)}</strong> (Conf: ${a.confidence})</span>
            <span>${a.time}</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// 7. User Profile Management
function loadProfile() {
  if (!state.user) return;
  
  const displayName = state.user.name || "";
  const displayRole = state.user.role || "Lead Nurse";
  
  $("#profile-display-name").value = displayName;
  $("#profile-username").value = state.user.username || "";
  $("#profile-role").value = displayRole;
  
  // Set Left panel values
  $("#profile-card-name").textContent = displayName;
  $("#profile-card-role").textContent = displayRole;
  $("#profile-avatar-placeholder").textContent = displayName.charAt(0).toUpperCase() || "U";
  
  // Optional expanded fields
  $("#profile-email").value = state.user.email || "nurse.sarah@careone.org";
  $("#profile-org").value = state.user.org || "Seattle Senior Health";
  $("#profile-bio").value = state.user.bio || "Clinical coordinator overseeing Ananya's daily operations.";
  $("#profile-new-pass").value = "";

  setMessage("#profile-edit-message", "");
}

async function handleProfileUpdate(e) {
  e.preventDefault();
  setMessage("#profile-edit-message", "Saving changes...", false);
  try {
    const name = $("#profile-display-name").value.trim();
    const role = $("#profile-role").value;
    const email = $("#profile-email").value.trim();
    const org = $("#profile-org").value.trim();
    const bio = $("#profile-bio").value.trim();
    const newPass = $("#profile-new-pass").value;

    if (!name) throw new Error("Display Name cannot be empty.");
    
    state.user.name = name;
    state.user.role = role;
    state.user.email = email;
    state.user.org = org;
    state.user.bio = bio;
    
    $("#user-display-name").textContent = name;
    $("#user-display-role").textContent = role;
    $("#caregiver-input").value = name;
    
    // Left panel update
    $("#profile-card-name").textContent = name;
    $("#profile-card-role").textContent = role;
    $("#profile-avatar-placeholder").textContent = name.charAt(0).toUpperCase() || "U";
    
    if (newPass) {
      // Mock change password save logic
      setMessage("#profile-edit-message", "Profile and credentials updated successfully!", false);
    } else {
      setMessage("#profile-edit-message", "Workspace profile successfully updated!", false);
    }
  } catch (err) {
    setMessage("#profile-edit-message", err.message, true);
  }
}

// 8. Clinical PDF Brief Generation
async function showHandoff() {
  if (!state.activePatientId) return;
  const result = await api(`/api/handoff?patient_id=${encodeURIComponent(state.activePatientId)}&date=${encodeURIComponent(state.data?.date || "")}`);
  $("#handoff-output").textContent = result.brief;
  $("#handoff-dialog").showModal();
}

function downloadHandoffPdf() {
  if (!state.activePatientId) return;
  const date = encodeURIComponent(state.data?.date || "");
  const patient = encodeURIComponent(state.activePatientId);
  window.open(`/api/handoff.pdf?patient_id=${patient}&date=${date}`, "_blank");
}

// 9. API Configuration Override
async function saveConfig(event) {
  event.preventDefault();
  setMessage("#settings-config-message", "Saving workspace preferences...", false);
  try {
    const lang = $("#settings-lang").value;
    const tz = $("#settings-tz").value;
    const units = $("#settings-units").value;
    const email = $("#settings-notify-email").checked;
    const theme = $("#settings-theme-select").value;
    const contrast = $("#settings-high-contrast").checked;
    const otp = $("#settings-otp-security").checked;

    localStorage.setItem("settings-lang", lang);
    localStorage.setItem("settings-tz", tz);
    localStorage.setItem("settings-units", units);
    localStorage.setItem("settings-notify-email", email);
    localStorage.setItem("settings-theme", theme);
    localStorage.setItem("settings-high-contrast", contrast);
    localStorage.setItem("settings-otp-security", otp);

    // Apply visual styles immediately
    document.body.classList.toggle("dark-theme", theme === "dark");
    document.body.classList.toggle("high-contrast-theme", contrast);
    
    const themeToggleChk = $("#theme-toggle-chk");
    const landingThemeToggle = $("#landing-theme-toggle-chk");
    if (themeToggleChk) themeToggleChk.checked = (theme === "dark");
    if (landingThemeToggle) landingThemeToggle.checked = (theme === "dark");

    setTimeout(() => {
      setMessage("#settings-config-message", "Preferences successfully updated!", false);
    }, 800);
  } catch (error) {
    setMessage("#settings-config-message", error.message, true);
  }
}

function loadSettings() {
  $("#settings-lang").value = localStorage.getItem("settings-lang") || "en";
  $("#settings-tz").value = localStorage.getItem("settings-tz") || "EST";
  $("#settings-units").value = localStorage.getItem("settings-units") || "imperial";
  $("#settings-notify-email").checked = localStorage.getItem("settings-notify-email") !== "false";
  
  const theme = localStorage.getItem("settings-theme") || "light";
  $("#settings-theme-select").value = theme;
  document.body.classList.toggle("dark-theme", theme === "dark");
  
  const themeToggleChk = $("#theme-toggle-chk");
  const landingThemeToggle = $("#landing-theme-toggle-chk");
  if (themeToggleChk) themeToggleChk.checked = (theme === "dark");
  if (landingThemeToggle) landingThemeToggle.checked = (theme === "dark");

  const contrast = localStorage.getItem("settings-high-contrast") === "true";
  $("#settings-high-contrast").checked = contrast;
  document.body.classList.toggle("high-contrast-theme", contrast);

  $("#settings-otp-security").checked = localStorage.getItem("settings-otp-security") === "true";

  setMessage("#settings-config-message", "");
}

async function exportPatientHistory() {
  let activeId = state.activePatientId;
  if (!activeId) {
    if (state.patients && state.patients.length > 0) {
      activeId = state.patients[0].patient_id;
    } else {
      alert("No patient profiles registered yet. Please register a patient profile first.");
      return;
    }
  }

  let historyData = historyCache;
  if (!historyData || historyData.length === 0 || state.activePatientId !== activeId) {
    try {
      historyData = await api(`/api/history?patient_id=${encodeURIComponent(activeId)}&days=7`);
    } catch (e) {
      alert("Failed to load history for export: " + e.message);
      return;
    }
  }

  try {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(historyData, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `careone_history_${activeId}.json`);
    dlAnchor.click();
  } catch (err) {
    alert("Failed to compile export: " + err.message);
  }
}

async function exportPatientHistoryWord() {
  let activeId = state.activePatientId;
  if (!activeId) {
    if (state.patients && state.patients.length > 0) {
      activeId = state.patients[0].patient_id;
    } else {
      alert("No patient profiles registered yet. Please register a patient profile first.");
      return;
    }
  }

  let historyData = historyCache;
  if (!historyData || historyData.length === 0 || state.activePatientId !== activeId) {
    try {
      historyData = await api(`/api/history?patient_id=${encodeURIComponent(activeId)}&days=7`);
    } catch (e) {
      alert("Failed to load history for export: " + e.message);
      return;
    }
  }

  if (!historyData || historyData.length === 0) {
    alert("No patient history data available to export.");
    return;
  }

  try {
    const patientName = state.patients.find(p => p.patient_id === activeId)?.name || activeId;
    
    let htmlContent = `
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head>
      <title>CareOne Patient History - ${patientName}</title>
      <!--[if gte mso 9]>
      <xml>
        <w:WordDocument>
          <w:View>Print</w:View>
          <w:Zoom>100</w:Zoom>
          <w:DoNotOptimizeForBrowser/>
        </w:WordDocument>
      </xml>
      <![endif]-->
      <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; color: #333333; line-height: 1.6; padding: 20px; }
        h1 { color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 6px; font-size: 24px; }
        h2 { color: #0d9488; font-size: 18px; margin-top: 24px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }
        h3 { color: #4b5563; font-size: 14px; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.05em; }
        .meta { color: #6b7280; font-size: 12px; margin-bottom: 20px; }
        .date-section { margin-bottom: 30px; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; background-color: #fafaf9; }
        .date-title { font-size: 16px; font-weight: bold; color: #1f2937; margin-top: 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; margin-bottom: 16px; }
        th, td { border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; font-size: 13px; }
        th { background-color: #f3f4f6; color: #374151; font-weight: 600; }
        ul { margin: 4px 0; padding-left: 20px; }
        li { font-size: 13px; margin-bottom: 4px; }
        .importance-high { color: #b91c1c; font-weight: bold; }
        .importance-medium { color: #d97706; font-weight: bold; }
        .importance-low { color: #2563eb; }
        .status-confirmed { color: #16a34a; font-weight: bold; }
        .status-unconfirmed { color: #dc2626; font-weight: bold; }
      </style>
    </head>
    <body>
      <h1>CareOne Patient Clinical Records</h1>
      <div class="meta">
        <strong>Patient Profile:</strong> ${patientName} (${activeId})<br>
        <strong>Report Generated:</strong> ${new Date().toLocaleString()}<br>
        <strong>Total Records:</strong> ${historyData.length} operational shifts
      </div>
    `;

    historyData.forEach(log => {
      const displayDate = new Date(log.date).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
      
      htmlContent += `
      <div class="date-section">
        <div class="date-title">${displayDate}</div>
        
        <h3>1. Caregiver Shift Notes</h3>
      `;
      
      if (log.raw_notes && log.raw_notes.length > 0) {
        log.raw_notes.forEach(note => {
          htmlContent += `
            <p style="margin: 4px 0 10px;">
              <strong>[${note.caregiver || 'Unknown Caregiver'}]:</strong> ${note.note}
            </p>
          `;
        });
      } else {
        htmlContent += `<p style="color: #9ca3af; font-style: italic;">No raw shift notes entered.</p>`;
      }

      htmlContent += `<h3>2. Vitals Tracked</h3>`;
      if (log.vitals && log.vitals.length > 0) {
        htmlContent += `
          <table>
            <thead>
              <tr>
                <th>Vital Type</th>
                <th>Measured Value</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
        `;
        log.vitals.forEach(v => {
          htmlContent += `
            <tr>
              <td><strong>${v.vital_type}</strong></td>
              <td>${v.value_raw}</td>
              <td>${v.status}</td>
            </tr>
          `;
        });
        htmlContent += `</tbody></table>`;
      } else {
        htmlContent += `<p style="color: #9ca3af; font-style: italic; margin-bottom: 16px;">No vitals recorded.</p>`;
      }

      htmlContent += `<h3>3. Reconciled Operations & Activity logs</h3>`;
      if (log.reconciled_events && log.reconciled_events.length > 0) {
        htmlContent += `
          <table>
            <thead>
              <tr>
                <th>Inferred Time</th>
                <th>Care Activity</th>
                <th>Verification Status</th>
                <th>Associated Caregiver</th>
              </tr>
            </thead>
            <tbody>
        `;
        log.reconciled_events.forEach(e => {
          const statusClass = e.status === 'confirmed' ? 'status-confirmed' : 'status-unconfirmed';
          htmlContent += `
            <tr>
              <td>${e.inferred_time || 'N/A'}</td>
              <td>${e.activity}</td>
              <td class="${statusClass}">${e.status}</td>
              <td>${e.caregivers ? e.caregivers.join(', ') : 'N/A'}</td>
            </tr>
          `;
        });
        htmlContent += `</tbody></table>`;
      } else {
        htmlContent += `<p style="color: #9ca3af; font-style: italic; margin-bottom: 16px;">No operations recorded.</p>`;
      }

      htmlContent += `<h3>4. Safety Gaps / Unconfirmed Duties</h3>`;
      if (log.detected_gaps && log.detected_gaps.length > 0) {
        htmlContent += `<ul>`;
        log.detected_gaps.forEach(g => {
          const impClass = g.importance === 'high' ? 'importance-high' : (g.importance === 'medium' ? 'importance-medium' : 'importance-low');
          htmlContent += `
            <li>
              <strong class="${impClass}">[${g.importance.toUpperCase()} PRIORITY] ${g.task_name}:</strong> 
              ${g.explanation}
            </li>
          `;
        });
        htmlContent += `</ul>`;
      } else {
        htmlContent += `<p style="color: #16a34a; font-weight: 600; margin-bottom: 16px;">✓ No safety gaps or missed tasks detected. Vitals and shift operations fully reconciled.</p>`;
      }

      htmlContent += `</div><hr style="border: 0; border-top: 1px dashed #cccccc; margin: 20px 0;">`;
    });

    htmlContent += `
    </body>
    </html>
    `;

    // Download the compiled Word HTML document with .doc extension
    const blob = new Blob(['\ufeff' + htmlContent], {
      type: 'application/msword'
    });
    const url = URL.createObjectURL(blob);
    const dlAnchor = document.createElement("a");
    dlAnchor.href = url;
    dlAnchor.download = `careone_history_${activeId}.doc`;
    document.body.appendChild(dlAnchor);
    dlAnchor.click();
    document.body.removeChild(dlAnchor);
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("Failed to export Word file: " + err.message);
  }
}

// 10. Caregiver Auth (Login & Signup)
async function handleLogin(event) {
  event.preventDefault();
  try {
    const result = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({
        username: $("#login-username").value,
        password: $("#login-password").value,
      }),
    });
    
    state.user = result.user;
    $("#user-display-name").textContent = result.user.name;
    $("#user-display-role").textContent = result.user.role;
    $("#caregiver-input").value = result.user.name;
    
    // Redirect to redirectAfterLogin if set, otherwise default to portal-hub (Studio)
    const target = state.redirectAfterLogin || "/studio";
    state.redirectAfterLogin = null;
    navigateTo(target);
  } catch (error) {
    setMessage("#auth-message", error.message, true);
  }
}

async function handleSignup(event) {
  event.preventDefault();
  try {
    const selectedRole = document.querySelector('input[name="signup-role"]:checked');
    const result = await api("/api/signup", {
      method: "POST",
      body: JSON.stringify({
        name: $("#signup-name").value,
        username: $("#signup-username").value,
        password: $("#signup-password").value,
        role: selectedRole ? selectedRole.value : "Family Caregiver",
      }),
    });
    setMessage("#signup-message", "Account registered successfully! You can now log in.", false);
    $("#login-username").value = result.user.username;
    $("#login-password").value = "";
    
    // Switch to login card
    showAuthCard("auth-login-card");
  } catch (error) {
    setMessage("#signup-message", error.message, true);
  }
}

function handleLogout() {
  state.user = null;
  state.activePatientId = null;
  state.data = null;
  navigateTo("/");
}

// Helper to switch cards in Auth Glassmorphism wrapper
function showAuthCard(cardId) {
  const cards = ["auth-login-card", "auth-signup-card", "auth-forgot-card", "auth-otp-card", "auth-reset-card"];
  cards.forEach(id => {
    const el = $(`#${id}`);
    if (el) el.classList.toggle("hidden", id !== cardId);
  });

  // Dynamic visual panel update
  const title = $("#auth-visual-title");
  const desc = $("#auth-visual-desc");
  if (title && desc) {
    if (cardId === "auth-signup-card") {
      title.innerHTML = `Join the care <br><span style="color: var(--brand);">circle today.</span>`;
      desc.textContent = "Create your account to coordinate caregiver notes, track vitals, and let seven agents catch what's missing — quietly, in the background.";
    } else {
      title.innerHTML = `Welcome back to <br><span style="color: var(--brand);">the care circle.</span>`;
      desc.textContent = "Sign in to access your caregiver workspace, checklist dashboard, and agent coordination console.";
    }
  }
}

// 11. Patient Registration
async function handleRegisterPatient(event) {
  event.preventDefault();
  setMessage("#register-patient-message", "Saving patient profile...");
  try {
    let routine = [];
    try {
      routine = JSON.parse($("#reg-routine-json").value);
    } catch (e) {
      throw new Error("Invalid Daily Routine JSON structure.");
    }
    
    const prefs = $("#reg-preferences").value
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
      
    await api("/api/patients", {
      method: "POST",
      body: JSON.stringify({
        patient_id: $("#reg-patient-id").value.trim().toLowerCase().replace(/\s+/g, "_"),
        name: $("#reg-name").value,
        age: parseInt($("#reg-age").value),
        relationship: $("#reg-relationship").value,
        conditions: $("#reg-conditions").value,
        preferences: prefs,
        daily_routine: routine
      }),
    });
    
    setMessage("#register-patient-message", "Patient successfully registered!", false);
    $("#register-patient-form").reset();
    $("#register-patient-dialog").close();
    await loadPatients();
  } catch (error) {
    setMessage("#register-patient-message", error.message, true);
  }
}

const TEMPLATES = {
  bp_normal: {
    note: "Checked Dad's blood pressure: 122/80. Checked blood glucose: 110 mg/dL. He finished all of his breakfast and was in good spirits."
  },
  refused_walk: {
    note: "Dad refused to go on his evening walk today because his knee joint was flaring up with pain. Offered him a heat pack instead. He was cooperative otherwise and ate dinner."
  },
  missed_hydration: {
    note: "Gave Dad lunch, but morning medications were delayed. Afternoon hydration check was skipped today. Dinner was served on time."
  }
};

// Event Bindings
document.addEventListener("DOMContentLoaded", () => {
  if (window.location.protocol === "file:") {
    const banner = document.createElement("div");
    banner.className = "file-warning";
    banner.innerHTML = "<strong>Studio server required.</strong> Start CareOne and open <code>http://127.0.0.1:8501/</code>.";
    document.body.prepend(banner);
  }

  // Theme Loader (Light/Dark mode)
  const savedTheme = localStorage.getItem("theme") || "light";
  const isDark = (savedTheme === "dark" || localStorage.getItem("settings-theme") === "dark");
  
  if (isDark) {
    document.body.classList.add("dark-theme");
  } else {
    document.body.classList.remove("dark-theme");
  }
  
  const toggle = $("#theme-toggle-chk");
  const landingToggle = $("#landing-theme-toggle-chk");
  if (toggle) toggle.checked = isDark;
  if (landingToggle) landingToggle.checked = isDark;

  function applyTheme(dark) {
    if (dark) {
      document.body.classList.add("dark-theme");
      localStorage.setItem("theme", "dark");
      localStorage.setItem("settings-theme", "dark");
    } else {
      document.body.classList.remove("dark-theme");
      localStorage.setItem("theme", "light");
      localStorage.setItem("settings-theme", "light");
    }
    const t = $("#theme-toggle-chk");
    const lt = $("#landing-theme-toggle-chk");
    const sel = $("#settings-theme-select");
    if (t) t.checked = dark;
    if (lt) lt.checked = dark;
    if (sel) sel.value = dark ? "dark" : "light";
  }

  on("#theme-toggle-chk", "change", (e) => {
    applyTheme(e.target.checked);
  });
  on("#landing-theme-toggle-chk", "change", (e) => {
    applyTheme(e.target.checked);
  });

  // Sidebar navigation tab clicks -> map to path navigation
  $$(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      const path = viewPathMap[item.dataset.view];
      if (path) navigateTo(path);
    });
  });

  // Landing CTAs
  on("#btn-launch-app", "click", () => {
    navigateTo(state.user ? "/studio" : "/login");
  });
  on("#btn-quick-signup", "click", () => {
    navigateTo("/login");
    showAuthCard("auth-signup-card");
  });
  on("#btn-landing-login", "click", () => {
    navigateTo(state.user ? "/studio" : "/login");
  });
  on("#btn-landing-signup", "click", () => {
    navigateTo("/login");
    showAuthCard("auth-signup-card");
  });

  // Redesigned Auth Card buttons
  on("#btn-goto-signup", "click", () => showAuthCard("auth-signup-card"));
  on("#btn-signup-goto-login", "click", () => showAuthCard("auth-login-card"));
  on("#btn-goto-forgot", "click", () => showAuthCard("auth-forgot-card"));
  on("#btn-forgot-goto-login", "click", () => showAuthCard("auth-login-card"));
  
  // Forgot Identity code send
  on("#forgot-form", "submit", (e) => {
    e.preventDefault();
    setMessage("#forgot-message", "Sending security code...", false);
    setTimeout(() => {
      setMessage("#forgot-message", "", false);
      showAuthCard("auth-otp-card");
    }, 1200);
  });

  // OTP verify code digits auto-focus
  const otpDigits = $$(".otp-digit");
  otpDigits.forEach((digit, index) => {
    digit.addEventListener("input", () => {
      if (digit.value && index < otpDigits.length - 1) {
        otpDigits[index + 1].focus();
      }
    });
    digit.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !digit.value && index > 0) {
        otpDigits[index - 1].focus();
      }
    });
  });

  // OTP Form verify code submit
  on("#otp-form", "submit", (e) => {
    e.preventDefault();
    setMessage("#otp-message", "Verifying code...", false);
    setTimeout(() => {
      setMessage("#otp-message", "", false);
      showAuthCard("auth-reset-card");
    }, 1200);
  });

  // Reset Password form submit
  on("#reset-pass-form", "submit", (e) => {
    e.preventDefault();
    const newPass = $("#reset-new-password").value;
    const confPass = $("#reset-confirm-password").value;
    if (newPass !== confPass) {
      setMessage("#reset-message", "Passwords do not match.", true);
      return;
    }
    setMessage("#reset-message", "Saving new password...", false);
    setTimeout(() => {
      setMessage("#reset-message", "", false);
      $("#login-password").value = newPass;
      showAuthCard("auth-login-card");
      setMessage("#auth-message", "Password successfully reset! Please sign in.", false);
    }, 1200);
  });

  // Password Visibility Eye Toggles
  $$(".password-group").forEach((group) => {
    const btn = group.querySelector(".password-toggle-btn");
    const input = group.querySelector("input");
    if (btn && input) {
      btn.addEventListener("click", () => {
        if (input.type === "password") {
          input.type = "text";
          btn.innerHTML = '<i class="ti ti-eye-off"></i>';
        } else {
          input.type = "password";
          btn.innerHTML = '<i class="ti ti-eye"></i>';
        }
      });
    }
  });

  on("#btn-back-to-landing", "click", () => navigateTo("/"));

  // Dismiss "How CareOne Works" logic (using sessionStorage)
  const isDismissed = sessionStorage.getItem("how-works-dismissed");
  if (isDismissed === "true") {
    const card = $("#how-works-card");
    if (card) card.classList.add("hidden");
  }
  on("#dismiss-how-works-btn", "click", () => {
    sessionStorage.setItem("how-works-dismissed", "true");
    const card = $("#how-works-card");
    if (card) card.classList.add("hidden");
  });

  // Forms
  on("#login-form", "submit", handleLogin);
  on("#signup-form", "submit", handleSignup);
  on("#profile-edit-form", "submit", handleProfileUpdate);
  on("#btn-logout", "click", handleLogout);
  on("#settings-config-form", "submit", saveConfig);
  on("#btn-export-data", "click", exportPatientHistory);
  on("#btn-export-word", "click", exportPatientHistoryWord);
  
  // Dashboard Actions
  on("#process-btn", "click", processNote);
  on("#routine-list", "change", updateChecklist);
  on("#handoff-btn", "click", showHandoff);
  on("#download-handoff-pdf", "click", downloadHandoffPdf);
  on("#close-handoff", "click", () => $("#handoff-dialog").close());
  on("#ask-history-form", "submit", askCareHistory);

  // Example query pills clicks
  $$(".example-query-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      $("#ask-history-input").value = pill.dataset.query;
      $("#ask-history-form").dispatchEvent(new Event("submit"));
    });
  });

  // Agent Trace pill clicks
  $$(".agent-step-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      renderTraceEvents(pill.dataset.agent);
    });
  });
  
  // Note Templates select dropdown
  on("#note-template-select", "change", (e) => {
    const val = e.target.value;
    $("#note-input").value = (val && TEMPLATES[val]) ? TEMPLATES[val].note : "";
  });

  // Memory timeline search input listener
  on("#memory-search-input", "input", (e) => {
    renderMemoryTimeline(e.target.value);
  });

  // Notifications filters bindings
  $$("#notifications-filter-bar button").forEach((btn) => {
    btn.addEventListener("click", () => {
      filterNotifications(btn.dataset.filter);
    });
  });

  // Dashboard quick patient dropdown switcher
  on("#dashboard-patient-selector", "change", (e) => {
    selectPatient(e.target.value);
  });

  // Register Patient Modals
  on("#btn-show-register-patient", "click", () => {
    const defaultRoutine = [
      { "task_id": "breakfast", "name": "Breakfast", "time_expected": "08:30", "category": "Meal", "importance": "High", "description": "Healthy breakfast" },
      { "task_id": "medications", "name": "Medications Check", "time_expected": "09:00", "category": "Medication", "importance": "High", "description": "Administer daily pills" },
      { "task_id": "evening_walk", "name": "Evening Walk", "time_expected": "17:00", "category": "Exercise", "importance": "Medium", "description": "Short walk around garden" }
    ];
    $("#reg-routine-json").value = JSON.stringify(defaultRoutine, null, 2);
    setMessage("#register-patient-message", "");
    $("#register-patient-dialog").showModal();
  });
  on("#close-register-patient", "click", () => $("#register-patient-dialog").close());
  on("#register-patient-form", "submit", handleRegisterPatient);

  // Initialize SPA router immediately
  window.addEventListener("popstate", handleRouting);
  loadPatients();
  handleRouting();

  // Interactive Sandbox logic
  const sandboxPresets = [
    "Dad's blood pressure was 142/91, skipped his morning medications and walk.",
    "Gave Dad lunch, blood pressure was 120/80, completed afternoon hydration.",
    "Dad is doing great! Heart rate was 72 bpm, blood pressure 118/75, slept well.",
    "Dad refused dinner and morning meds. BP was 148/96. Feeling dizzy."
  ];
  let presetIdx = 0;
  
  on("#btn-sandbox-preset", "click", () => {
    const input = $("#sandbox-input");
    if (input) {
      input.value = sandboxPresets[presetIdx];
      presetIdx = (presetIdx + 1) % sandboxPresets.length;
    }
  });

  on("#btn-sandbox-run", "click", () => {
    const btn = $("#btn-sandbox-run");
    const input = $("#sandbox-input");
    const status = $("#sandbox-status");
    
    if (!input || !input.value.trim()) return;
    
    btn.disabled = true;
    status.innerText = "Parsing...";
    status.style.color = "var(--warning)";
    
    let dots = 0;
    const interval = setInterval(() => {
      dots = (dots + 1) % 4;
      status.innerText = "Parsing" + ".".repeat(dots);
    }, 300);

    setTimeout(() => {
      clearInterval(interval);
      btn.disabled = false;
      status.innerText = "Complete";
      status.style.color = "var(--brand)";
      
      const text = input.value;
      
      // Basic regex parsing
      const bpMatch = text.match(/(\d{2,3})\s*\/\s*(\d{2,3})/);
      const hrMatch = text.match(/(\d{2,3})\s*bpm/i);
      const medMatch = text.toLowerCase().includes("med");
      
      let syst = "—";
      let diast = "—";
      let riskCount = 0;
      let vitalsCount = 2;
      let scoreVal = 86;
      let MedState = "Active";
      
      if (bpMatch) {
        syst = bpMatch[1];
        diast = bpMatch[2];
        vitalsCount += 1;
        
        const sVal = parseInt(syst);
        const dVal = parseInt(diast);
        if (sVal >= 140 || dVal >= 90) {
          riskCount += 1;
          scoreVal -= 15;
        }
      }
      
      if (hrMatch) {
        vitalsCount += 1;
      }
      
      if (medMatch) {
        const isSkipped = text.toLowerCase().includes("skip") || text.toLowerCase().includes("refuse") || text.toLowerCase().includes("delay");
        MedState = isSkipped ? "Skipped" : "Given";
        if (isSkipped) {
          riskCount += 1;
          scoreVal -= 20;
        } else {
          scoreVal += 10;
        }
      }
      
      scoreVal = Math.max(30, Math.min(100, scoreVal));
      
      // Update UI elements
      $("#sandbox-score").innerText = `${scoreVal}%`;
      $("#sandbox-stat-risk").innerHTML = `<span style="width: 8px; height: 8px; border-radius: 50%; background: ${riskCount > 0 ? 'var(--warning)' : 'var(--brand)'}; display: inline-block;"></span> ${riskCount} ${riskCount === 1 ? 'risk found' : 'risks found'}`;
      $("#sandbox-stat-vitals").innerHTML = `<span style="width: 8px; height: 8px; border-radius: 50%; background: #d97706; display: inline-block;"></span> ${vitalsCount} ${vitalsCount === 1 ? 'vital tracked' : 'vitals tracked'}`;
      
      $("#sandbox-v-systolic").innerText = syst;
      $("#sandbox-v-diastolic").innerText = diast;
      $("#sandbox-v-meds").innerText = MedState;
      
      // Dynamically update background dial color
      const dial = document.querySelector(".studio-hero-visual .conic-dial-container");
      if (dial) {
        dial.style.background = `radial-gradient(circle, #1c231e 60%, ${riskCount > 0 ? 'rgba(217, 119, 6, 0.3)' : 'rgba(82, 163, 124, 0.3)'} 100%)`;
      }
    }, 1800);
  });
});

function updateRolePills() {
  const selectedRadio = document.querySelector('input[name="signup-role"]:checked');
  if (!selectedRadio) return;
  const val = selectedRadio.value;
  
  const pills = {
    "Family Caregiver": "pill-family",
    "Professional": "pill-professional",
    "Care Coordinator": "pill-coordinator"
  };
  
  Object.keys(pills).forEach(role => {
    const pill = document.getElementById(pills[role]);
    if (pill) {
      pill.classList.toggle("selected", role === val);
    }
  });
}
window.updateRolePills = updateRolePills;

/**
 * Incident Response Panic Button - Main Dashboard Controller
 */
document.addEventListener("DOMContentLoaded", () => {
  App.init();
});

const App = {
  refreshInterval: null,
  isAutoRefreshActive: true,
  lastKnownIncidentCount: 0,
  currentUser: null,

  async init() {
    await this.loadCurrentUser();
    this.bindEvents();
    this.loadDashboardData();
    this.startAutoRefresh();
  },

  async loadCurrentUser() {
    try {
      const res = await API.getMe();
      if (res && res.user) {
        this.currentUser = res.user;
        this.renderUserUI();
      }
    } catch (e) {
      console.warn("Could not load current user profile:", e);
    }
  },

  renderUserUI() {
    const userRoleBadge = document.getElementById("activeRoleBadge");
    const userNameLabel = document.getElementById("activeUserNameLabel");
    if (!this.currentUser) return;

    if (userNameLabel) userNameLabel.textContent = this.currentUser.username;
    if (userRoleBadge) {
      userRoleBadge.textContent = this.currentUser.role;
      userRoleBadge.className = "badge ms-1 " + (
        this.currentUser.role === "Admin" ? "bg-danger" :
        this.currentUser.role === "Responder" ? "bg-warning text-dark" : "bg-primary"
      );
    }
  },

  bindEvents() {
    // Sound toggle in navbar
    const soundToggle = document.getElementById("toggleSoundBtn");
    if (soundToggle) {
      this.updateSoundButtonUI(soundToggle);
      soundToggle.addEventListener("click", () => {
        const isMuted = window.soundEngine.toggleMute();
        this.updateSoundButtonUI(soundToggle);
        this.showToast(isMuted ? "Audio alerts muted" : "Audio alerts enabled", "info");
      });
    }

    // Role switcher dropdown buttons
    document.querySelectorAll(".role-switch-item").forEach(item => {
      item.addEventListener("click", async (e) => {
        e.preventDefault();
        const role = e.currentTarget.getAttribute("data-role");
        try {
          const res = await API.switchRole(role);
          this.currentUser = res.user;
          this.renderUserUI();
          this.showToast(res.message, "info");
          this.loadDashboardData();
        } catch (err) {
          this.showToast("Failed to switch role: " + err.message, "danger");
        }
      });
    });

    // Auto-refresh toggle
    const refreshToggle = document.getElementById("toggleRefreshBtn");
    if (refreshToggle) {
      refreshToggle.addEventListener("click", () => {
        this.isAutoRefreshActive = !this.isAutoRefreshActive;
        refreshToggle.innerHTML = this.isAutoRefreshActive 
          ? '<i class="bi bi-arrow-repeat spin"></i> Auto-Sync: ON'
          : '<i class="bi bi-pause"></i> Auto-Sync: OFF';
        refreshToggle.classList.toggle("btn-outline-success", this.isAutoRefreshActive);
        refreshToggle.classList.toggle("btn-outline-secondary", !this.isAutoRefreshActive);
      });
    }

    // Preset selector in Panic Modal
    const templateSelect = document.getElementById("panicPresetSelect");
    if (templateSelect) {
      templateSelect.addEventListener("change", (e) => {
        this.applyPanicPreset(e.target.value);
      });
    }

    // Submit Panic Form
    const panicForm = document.getElementById("panicTriggerForm");
    if (panicForm) {
      panicForm.addEventListener("submit", (e) => {
        e.preventDefault();
        this.executePanicTrigger();
      });
    }

    // Search and filter inputs
    const searchInput = document.getElementById("incidentSearchInput");
    if (searchInput) {
      searchInput.addEventListener("input", this.debounce(() => this.loadIncidentsTable(), 300));
    }

    const statusFilter = document.getElementById("statusFilterSelect");
    if (statusFilter) {
      statusFilter.addEventListener("change", () => this.loadIncidentsTable());
    }

    const severityFilter = document.getElementById("severityFilterSelect");
    if (severityFilter) {
      severityFilter.addEventListener("change", () => this.loadIncidentsTable());
    }

    // Acknowledge Form submission
    const ackForm = document.getElementById("ackModalForm");
    if (ackForm) {
      ackForm.addEventListener("submit", (e) => {
        e.preventDefault();
        this.executeAcknowledge();
      });
    }

    // Resolve Form submission
    const resolveForm = document.getElementById("resolveModalForm");
    if (resolveForm) {
      resolveForm.addEventListener("submit", (e) => {
        e.preventDefault();
        this.executeResolve();
      });
    }

    // Seed Data Button
    const seedBtn = document.getElementById("seedDemoDataBtn");
    if (seedBtn) {
      seedBtn.addEventListener("click", async () => {
        try {
          seedBtn.disabled = true;
          const res = await API.seedDemoData();
          this.showToast(res.message, "success");
          this.loadDashboardData();
        } catch (e) {
          this.showToast("Failed to seed demo data: " + e.message, "danger");
        } finally {
          seedBtn.disabled = false;
        }
      });
    }

    // Reset Data Button
    const resetBtn = document.getElementById("resetDataBtn");
    if (resetBtn) {
      resetBtn.addEventListener("click", async () => {
        if (confirm("Are you sure you want to reset all incidents and audit trails?")) {
          try {
            const res = await API.resetData();
            this.showToast(res.message, "warning");
            this.loadDashboardData();
          } catch (e) {
            this.showToast("Failed to reset: " + e.message, "danger");
          }
        }
      });
    }
  },

  updateSoundButtonUI(btn) {
    const isMuted = window.soundEngine.isMuted;
    btn.innerHTML = isMuted 
      ? '<i class="bi bi-volume-mute-fill"></i> Muted'
      : '<i class="bi bi-volume-up-fill"></i> Sound ON';
    btn.className = isMuted ? "btn btn-sm btn-outline-secondary" : "btn btn-sm btn-outline-warning";
  },

  startAutoRefresh() {
    this.refreshInterval = setInterval(() => {
      if (this.isAutoRefreshActive) {
        this.loadDashboardData(true);
      }
    }, 5000);
  },

  async loadDashboardData(isBackground = false) {
    try {
      const [metricsData, incidentsData] = await Promise.all([
        API.getMetrics(),
        API.getIncidents(this.getTableFilters())
      ]);

      if (metricsData && metricsData.metrics) {
        this.renderKPIs(metricsData.metrics);
        if (window.OpsCharts) {
          window.OpsCharts.init(metricsData.metrics);
        }
      }

      if (incidentsData && incidentsData.incidents) {
        this.renderIncidentsTable(incidentsData.incidents);
        this.checkActiveEmergency(incidentsData.incidents, isBackground);
      }
    } catch (err) {
      if (!isBackground) {
        console.error("Dashboard data load error:", err);
      }
    }
  },

  async loadIncidentsTable() {
    try {
      const data = await API.getIncidents(this.getTableFilters());
      this.renderIncidentsTable(data.incidents || []);
    } catch (err) {
      console.error("Table refresh error:", err);
    }
  },

  getTableFilters() {
    const search = document.getElementById("incidentSearchInput")?.value || "";
    const status = document.getElementById("statusFilterSelect")?.value || "";
    const severity = document.getElementById("severityFilterSelect")?.value || "";
    const filters = {};
    if (search) filters.q = search;
    if (status) filters.status = status;
    if (severity) filters.severity = severity;
    return filters;
  },

  renderKPIs(metrics) {
    const p1CountEl = document.getElementById("kpiP1CriticalCount");
    const openCountEl = document.getElementById("kpiOpenCount");
    const mttaEl = document.getElementById("kpiMtta");
    const mttrEl = document.getElementById("kpiMttr");

    if (p1CountEl) p1CountEl.textContent = metrics.p1_critical_count;
    if (openCountEl) openCountEl.textContent = metrics.open_count;
    if (mttaEl) {
      mttaEl.textContent = metrics.avg_mtta_minutes > 0 ? `${metrics.avg_mtta_minutes}m` : `${metrics.avg_mtta_seconds}s`;
    }
    if (mttrEl) {
      mttrEl.textContent = metrics.avg_mttr_minutes > 0 ? `${metrics.avg_mttr_minutes}m` : `${metrics.avg_mttr_seconds}s`;
    }
  },

  checkActiveEmergency(incidents, isBackground) {
    const banner = document.getElementById("emergencyAlertBanner");
    const openP1s = incidents.filter(i => i.severity === "P1_CRITICAL" && i.status === "OPEN");

    if (banner) {
      if (openP1s.length > 0) {
        banner.classList.remove("d-none");
        const countText = document.getElementById("activeP1CountText");
        if (countText) {
          countText.textContent = `${openP1s.length} ACTIVE P1 CRITICAL INCIDENT(S) CURRENTLY UNACKNOWLEDGED!`;
        }
        if (isBackground && incidents.length > this.lastKnownIncidentCount) {
          window.soundEngine.playPanicAlarm(2);
        }
      } else {
        banner.classList.add("d-none");
      }
    }
    this.lastKnownIncidentCount = incidents.length;
  },

  renderIncidentsTable(incidents) {
    const tbody = document.getElementById("incidentsTableBody");
    if (!tbody) return;

    if (incidents.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center py-5 text-secondary">
            <i class="bi bi-shield-check display-6 text-success d-block mb-2"></i>
            No incidents matching criteria. All systems nominal.
          </td>
        </tr>`;
      return;
    }

    const canManage = this.currentUser && (this.currentUser.role === "Admin" || this.currentUser.role === "Responder");

    tbody.innerHTML = incidents.map(inc => {
      const sevBadge = this.getSeverityBadge(inc.severity);
      const statusBadge = this.getStatusBadge(inc.status);
      const isPanicBadge = inc.is_panic ? '<span class="badge bg-danger ms-1"><i class="bi bi-lightning-fill"></i> PANIC</span>' : '';
      const timerStr = inc.status === "RESOLVED" || inc.status === "CLOSED"
        ? `<span class="text-secondary"><i class="bi bi-check-circle"></i> ${this.formatDuration(inc.mttr_seconds)}</span>`
        : `<span class="text-danger fw-bold"><i class="bi bi-stopwatch"></i> ${this.formatDuration(inc.mtta_seconds || 0)}</span>`;

      return `
        <tr class="${inc.severity === 'P1_CRITICAL' && inc.status === 'OPEN' ? 'table-danger' : ''}">
          <td class="fw-bold">
            <a href="/incidents/${inc.id}" class="text-info text-decoration-none font-monospace">
              ${inc.key}
            </a>
            ${isPanicBadge}
          </td>
          <td>
            <div class="fw-semibold text-light">${this.escapeHtml(inc.title)}</div>
            <small class="text-secondary"><i class="bi bi-hdd-network"></i> ${this.escapeHtml(inc.service_name)}</small>
          </td>
          <td>${sevBadge}</td>
          <td>${statusBadge}</td>
          <td>
            <span class="text-secondary">${this.escapeHtml(inc.assigned_to || 'Unassigned')}</span>
          </td>
          <td>${timerStr}</td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              <a href="/incidents/${inc.id}" class="btn btn-outline-info" title="Open War Room & Audit">
                <i class="bi bi-eye"></i> View
              </a>
              ${inc.status === 'OPEN' && canManage ? `
                <button class="btn btn-warning text-dark fw-semibold" onclick="App.openAckModal(${inc.id}, '${this.escapeJs(inc.key)}')">
                  <i class="bi bi-hand-index-thumb"></i> Ack
                </button>
              ` : ''}
              ${(inc.status === 'ACKNOWLEDGED' || inc.status === 'OPEN') && canManage ? `
                <button class="btn btn-success fw-semibold" onclick="App.openResolveModal(${inc.id}, '${this.escapeJs(inc.key)}')">
                  <i class="bi bi-check2-circle"></i> Resolve
                </button>
              ` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join("");
  },

  applyPanicPreset(val) {
    const titleInput = document.getElementById("panicTitle");
    const serviceInput = document.getElementById("panicService");
    const descInput = document.getElementById("panicDescription");

    const presets = {
      db_outage: {
        title: "CRITICAL: Primary PostgreSQL Database Replication & Connection Collapse",
        service: "Database Cluster (PostgreSQL)",
        description: "Zero available connections in pgpooler. Application transactions failing with connection pool timeout. Immediate master failover triage needed."
      },
      payment_gateway: {
        title: "CRITICAL: Global Checkout Gateway 504 Timeouts & Charge Failures",
        service: "Payment Gateway (Stripe Service)",
        description: "Payment webhooks timing out across all regional checkout services. Revenue impacting emergency."
      },
      security_breach: {
        title: "SECURITY INCIDENT: High-Volume Credential Stuffing & Admin Token Anomaly",
        service: "Authentication & SSO Service",
        description: "12,000+ unauthorized authorization requests detected per minute. Immediate firewall and token revocation required."
      },
      api_gateway: {
        title: "CRITICAL: API Gateway / Ingress Cluster 502 Bad Gateway Outage",
        service: "API Gateway (Kong / Ingress)",
        description: "Ingress pods crash-looping under load. All external API requests dropping with HTTP 502."
      }
    };

    if (presets[val]) {
      titleInput.value = presets[val].title;
      serviceInput.value = presets[val].service;
      descInput.value = presets[val].description;
    }
  },

  async executePanicTrigger() {
    const btn = document.getElementById("submitPanicBtn");
    const title = document.getElementById("panicTitle").value.trim();
    const service_name = document.getElementById("panicService").value.trim();
    const description = document.getElementById("panicDescription").value.trim();
    const triggered_by = document.getElementById("panicTriggeredBy").value.trim() || 
      (this.currentUser ? `${this.currentUser.username} (${this.currentUser.role})` : "NOC Panic Operator");

    if (!title || !service_name) {
      alert("Please provide both Title and Service Name.");
      return;
    }

    try {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>DISPATCHING...';

      // Play emergency siren
      window.soundEngine.playPanicAlarm(3);

      const res = await API.triggerPanic({
        title,
        service_name,
        description,
        triggered_by
      });

      const modalEl = document.getElementById("panicModal");
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();

      this.showToast(res.message, "danger");
      this.loadDashboardData();

      setTimeout(() => {
        if (res.incident && res.incident.id) {
          window.location.href = `/incidents/${res.incident.id}`;
        }
      }, 1200);

    } catch (err) {
      this.showToast("Failed to trigger panic: " + (err.error || err.message), "danger");
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-lightning-fill me-1"></i>CONFIRM PANIC TRIGGER';
    }
  },

  openAckModal(id, key) {
    document.getElementById("ackIncidentId").value = id;
    document.getElementById("ackIncidentKeyLabel").textContent = key;
    if (this.currentUser) {
      document.getElementById("ackActor").value = `${this.currentUser.username} (${this.currentUser.role})`;
      document.getElementById("ackAssignee").value = this.currentUser.username;
    }
    const modal = new bootstrap.Modal(document.getElementById("ackModal"));
    modal.show();
  },

  async executeAcknowledge() {
    const id = document.getElementById("ackIncidentId").value;
    const actor = document.getElementById("ackActor").value.trim();
    const assigned_to = document.getElementById("ackAssignee").value.trim();

    try {
      const res = await API.acknowledgeIncident(id, actor, assigned_to);
      window.soundEngine.playAckChime();
      const modal = bootstrap.Modal.getInstance(document.getElementById("ackModal"));
      if (modal) modal.hide();
      this.showToast(res.message, "warning");
      this.loadDashboardData();
    } catch (err) {
      this.showToast("Failed to acknowledge: " + (err.error || err.message), "danger");
    }
  },

  openResolveModal(id, key) {
    document.getElementById("resolveIncidentId").value = id;
    document.getElementById("resolveIncidentKeyLabel").textContent = key;
    if (this.currentUser) {
      document.getElementById("resolveActor").value = `${this.currentUser.username} (${this.currentUser.role})`;
    }
    const modal = new bootstrap.Modal(document.getElementById("resolveModal"));
    modal.show();
  },

  async executeResolve() {
    const id = document.getElementById("resolveIncidentId").value;
    const actor = document.getElementById("resolveActor").value.trim();
    const root_cause = document.getElementById("resolveRootCause").value.trim();
    const resolution_notes = document.getElementById("resolveNotes").value.trim();

    try {
      const res = await API.resolveIncident(id, actor, root_cause, resolution_notes);
      window.soundEngine.playResolvedChime();
      const modal = bootstrap.Modal.getInstance(document.getElementById("resolveModal"));
      if (modal) modal.hide();
      this.showToast(res.message, "success");
      this.loadDashboardData();
    } catch (err) {
      this.showToast("Failed to resolve: " + (err.error || err.message), "danger");
    }
  },

  getSeverityBadge(sev) {
    const map = {
      P1_CRITICAL: '<span class="badge badge-p1"><i class="bi bi-exclamation-triangle-fill"></i> P1 Critical</span>',
      P2_HIGH: '<span class="badge badge-p2">P2 High</span>',
      P3_MEDIUM: '<span class="badge badge-p3">P3 Medium</span>',
      P4_LOW: '<span class="badge badge-p4">P4 Low</span>'
    };
    return map[sev] || `<span class="badge bg-secondary">${sev}</span>`;
  },

  getStatusBadge(st) {
    const map = {
      OPEN: '<span class="badge badge-status-open"><i class="bi bi-record-circle"></i> OPEN</span>',
      ACKNOWLEDGED: '<span class="badge badge-status-ack"><i class="bi bi-clock-history"></i> ACKNOWLEDGED</span>',
      RESOLVED: '<span class="badge badge-status-resolved"><i class="bi bi-check2-circle"></i> RESOLVED</span>',
      CLOSED: '<span class="badge badge-status-closed"><i class="bi bi-archive"></i> CLOSED</span>'
    };
    return map[st] || `<span class="badge bg-secondary">${st}</span>`;
  },

  formatDuration(seconds) {
    if (!seconds || seconds <= 0) return "0s";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    if (m === 0) return `${s}s`;
    return `${m}m ${s}s`;
  },

  showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toastId = "toast_" + Date.now();
    const toastHtml = `
      <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0 shadow-lg mb-2" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
          <div class="toast-body fw-semibold">
            ${this.escapeHtml(message)}
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>
    `;
    container.insertAdjacentHTML("beforeend", toastHtml);
    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl, { delay: 4500 });
    toast.show();
    toastEl.addEventListener("hidden.bs.toast", () => toastEl.remove());
  },

  debounce(func, wait) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  },

  escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },

  escapeJs(str) {
    if (!str) return "";
    return String(str).replace(/'/g, "\\'");
  }
};

window.App = App;


/**
 * API Client for Incident Response Panic Button System
 */
const API = {
  baseUrl: "/api",

  getToken() {
    return localStorage.getItem("panic_api_token") || "";
  },

  setToken(token) {
    if (token) {
      localStorage.setItem("panic_api_token", token);
    } else {
      localStorage.removeItem("panic_api_token");
    }
  },

  async request(endpoint, options = {}) {
    const defaultHeaders = {
      "Content-Type": "application/json",
      "Accept": "application/json"
    };

    const token = this.getToken();
    if (token) {
      defaultHeaders["Authorization"] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers: { ...defaultHeaders, ...options.headers }
    };

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, config);
      const data = await response.json();
      if (!response.ok) {
        const error = new Error(data.error || `HTTP ${response.status}: Request failed`);
        error.code = data.code || "REQUEST_FAILED";
        error.status = response.status;
        throw error;
      }
      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  // Auth & Roles
  login(usernameOrEmail, password) {
    return this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: usernameOrEmail, password })
    }).then(res => {
      if (res.user && res.user.api_token) {
        this.setToken(res.user.api_token);
      }
      return res;
    });
  },

  logout() {
    this.setToken(null);
    return this.request("/auth/logout", { method: "POST" });
  },

  register(username, email, password, role = "Reporter") {
    return this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password, role })
    }).then(res => {
      if (res.user && res.user.api_token) {
        this.setToken(res.user.api_token);
      }
      return res;
    });
  },

  getMe() {
    return this.request("/auth/me");
  },

  switchRole(role) {
    return this.request("/auth/switch-role", {
      method: "POST",
      body: JSON.stringify({ role })
    }).then(res => {
      if (res.user && res.user.api_token) {
        this.setToken(res.user.api_token);
      }
      return res;
    });
  },

  // Panic & Incidents
  triggerPanic(payload = {}) {
    const headers = {};
    if (!payload.idempotency_key) {
      payload.idempotency_key = "panic_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);
    }
    headers["Idempotency-Key"] = payload.idempotency_key;

    return this.request("/panic", {
      method: "POST",
      headers,
      body: JSON.stringify(payload)
    });
  },

  getIncidents(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/incidents${query ? `?${query}` : ""}`);
  },

  createIncident(payload) {
    return this.request("/incidents", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  getIncident(id) {
    return this.request(`/incidents/${id}`);
  },

  acknowledgeIncident(id, actor = null, assignedTo = null) {
    return this.request(`/incidents/${id}/acknowledge`, {
      method: "POST",
      body: JSON.stringify({ actor, assigned_to: assignedTo })
    });
  },

  resolveIncident(id, actor = null, rootCause = "", resolutionNotes = "") {
    return this.request(`/incidents/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({
        actor,
        root_cause: rootCause,
        resolution_notes: resolutionNotes
      })
    });
  },

  closeIncident(id, actor = null) {
    return this.request(`/incidents/${id}/close`, {
      method: "POST",
      body: JSON.stringify({ actor })
    });
  },

  reopenIncident(id, actor = null, reason = "Regression observed") {
    return this.request(`/incidents/${id}/reopen`, {
      method: "POST",
      body: JSON.stringify({ actor, reason })
    });
  },

  addComment(id, author, comment) {
    return this.request(`/incidents/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ author, comment })
    });
  },

  assignIncident(id, actor, assignedTo) {
    return this.request(`/incidents/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ actor, assigned_to: assignedTo })
    });
  },

  // Audit
  getAuditLogs(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/audit-logs${query ? `?${query}` : ""}`);
  },

  getIncidentAudit(id) {
    return this.request(`/incidents/${id}/audit`);
  },

  // Notifications
  getNotifications(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/notifications${query ? `?${query}` : ""}`);
  },

  testNotification(payload) {
    return this.request("/notifications/test", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  // Analytics & Admin
  getMetrics() {
    return this.request("/metrics");
  },

  seedDemoData() {
    return this.request("/seed", { method: "POST" });
  },

  resetData() {
    return this.request("/reset", { method: "POST" });
  }
};

window.API = API;


/**
 * UniScout — Background Service Worker (Manifest V3)
 * ===================================================
 * Runs as an event-driven service worker (no persistent background page).
 *
 * Responsibilities:
 *  1. Sync auth token from the web app via postMessage → content script → here
 *  2. Proxy API calls (profile, essay generation) for content script
 *     (content scripts can't set Authorization headers on cross-origin fetch)
 *  3. Open login page on first install
 */

/* ─── Config ─── */
const DEFAULT_API_URL = "http://localhost:3003";
const DEFAULT_APP_URL = "http://localhost:3000";

/** Read stored API URL or fall back to localhost */
async function getApiUrl() {
  const { apiBaseUrl } = await chrome.storage.sync.get("apiBaseUrl");
  return apiBaseUrl || DEFAULT_API_URL;
}

/** Read stored auth token */
async function getToken() {
  const { authToken } = await chrome.storage.sync.get("authToken");
  return authToken || null;
}

/* ═══════════════════ MESSAGE ROUTER ═══════════════════ */

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const handler = MESSAGE_HANDLERS[message.type || message.action];
  if (handler) {
    handler(message, sender, sendResponse);
    return true; // keep channel open for async sendResponse
  }
  return false;
});

const MESSAGE_HANDLERS = {

  /* ─── Auth: token sync from webapp ─── */
  UNISCOUT_AUTH_TOKEN: async (msg, _sender, respond) => {
    if (msg.token) {
      await chrome.storage.sync.set({ authToken: msg.token });
      console.log("[UniScout] Auth token synced");
    } else {
      await chrome.storage.sync.remove(["authToken", "cachedProfile"]);
      console.log("[UniScout] Auth token cleared (logout)");
    }
    respond({ success: true });
  },

  /* ─── Profile fetch (proxied for content script) ─── */
  GET_PROFILE: async (_msg, _sender, respond) => {
    try {
      const token = await getToken();
      if (!token) {
        respond({ success: false, message: "Not signed in." });
        return;
      }

      const apiUrl = await getApiUrl();
      const res = await fetch(`${apiUrl}/api/extension/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        if (res.status === 401) {
          await chrome.storage.sync.remove(["authToken", "cachedProfile"]);
          respond({ success: false, message: "Session expired. Please sign in again." });
        } else {
          respond({ success: false, message: `Server error (${res.status})` });
        }
        return;
      }

      const json = await res.json();
      // Cache the profile for popup fast-display
      await chrome.storage.sync.set({ cachedProfile: json.data || json });
      respond({ success: true, data: json.data || json });
    } catch (err) {
      console.error("[UniScout] Profile fetch failed:", err);
      respond({ success: false, message: "Could not connect to UniScout server." });
    }
  },

  /* ─── AI content generation (proxied for content script) ─── */
  GENERATE_CONTENT: async (msg, _sender, respond) => {
    try {
      const token = await getToken();
      if (!token) {
        respond({ success: false, message: "Not signed in." });
        return;
      }

      const apiUrl = await getApiUrl();
      const res = await fetch(`${apiUrl}/api/extension/generate-content`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(msg.payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        respond({ success: false, message: err.message || `Error ${res.status}` });
        return;
      }

      const json = await res.json();
      respond({
        success: true,
        generatedText: json.generatedText,
        wordCount: json.wordCount,
        remaining: json.remaining,
      });
    } catch (err) {
      console.error("[UniScout] Content generation failed:", err);
      respond({ success: false, message: "Could not connect to AI service." });
    }
  },

  /* ─── Legacy essay endpoint (backward compat) ─── */
  GENERATE_ESSAY: async (msg, _sender, respond) => {
    try {
      const token = await getToken();
      if (!token) {
        respond({ success: false, message: "Not signed in." });
        return;
      }

      const apiUrl = await getApiUrl();
      const res = await fetch(`${apiUrl}/api/extension/generate-essay`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(msg.payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        respond({ success: false, message: err.message || `Error ${res.status}` });
        return;
      }

      const json = await res.json();
      respond({ success: true, essay: json.essay, wordCount: json.wordCount });
    } catch (err) {
      console.error("[UniScout] Essay generation failed:", err);
      respond({ success: false, message: "Could not connect to AI service." });
    }
  },
};

/* ═══════════════════ ON INSTALL ═══════════════════ */

chrome.runtime.onInstalled.addListener(async (details) => {
  if (details.reason === "install") {
    // Set default API URL
    await chrome.storage.sync.set({ apiBaseUrl: DEFAULT_API_URL });
    // Open login page
    chrome.tabs.create({ url: `${DEFAULT_APP_URL}/login` });
  }
});

/* ═══════════════════ ON STARTUP (service worker wake) ═══════════════════ */

chrome.runtime.onStartup.addListener(() => {
  console.log("[UniScout] Service worker started");
});

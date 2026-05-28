/**
 * UniScout Chrome Extension — Popup Logic
 * ========================================
 * Manages 3 states: logged-out → no-form → form-detected.
 * Communicates with content.js via chrome.tabs.sendMessage.
 */

(() => {
  "use strict";

  /* ─── DOM refs ─── */
  const $loading    = document.getElementById("state-loading");
  const $loggedOut  = document.getElementById("state-logged-out");
  const $noForm     = document.getElementById("state-no-form");
  const $formState  = document.getElementById("state-form");

  const $btnLogin   = document.getElementById("btn-login");
  const $btnGoApp   = document.getElementById("btn-go-app");
  const $btnFill    = document.getElementById("btn-autofill");
  const $btnRescan  = document.getElementById("btn-rescan");
  const $btnLogout1 = document.getElementById("btn-logout-1");
  const $btnLogout2 = document.getElementById("btn-logout-2");

  const $fieldCount = document.getElementById("field-count");
  const $aiToggle   = document.getElementById("ai-toggle");
  const $fillStatus = document.getElementById("fill-status");
  const $progressFill = document.getElementById("progress-fill");
  const $progressText = document.getElementById("progress-text");

  /* ─── Helpers ─── */

  const show = (el) => el.removeAttribute("hidden");
  const hide = (el) => el.setAttribute("hidden", "");

  const showState = (stateEl) => {
    [$loading, $loggedOut, $noForm, $formState].forEach(hide);
    show(stateEl);
  };

  const getStorage = (keys) =>
    new Promise((resolve) => chrome.storage.sync.get(keys, resolve));

  const setStorage = (obj) =>
    new Promise((resolve) => chrome.storage.sync.set(obj, resolve));

  const removeStorage = (keys) =>
    new Promise((resolve) => chrome.storage.sync.remove(keys, resolve));

  /** Get the active tab */
  const getActiveTab = () =>
    new Promise((resolve) =>
      chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) =>
        resolve(tab)
      )
    );

  /** Send message to content script in active tab */
  const sendToContent = (action, data = {}) =>
    new Promise(async (resolve) => {
      const tab = await getActiveTab();
      if (!tab?.id) return resolve(null);
      chrome.tabs.sendMessage(tab.id, { action, ...data }, (response) => {
        resolve(chrome.runtime.lastError ? null : response);
      });
    });

  const initials = (name) =>
    (name || "")
      .split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) || "?";

  /* ─── Populate profile UI elements ─── */

  const fillProfileUI = (profile) => {
    const name = profile.firstName
      ? `${profile.firstName} ${profile.lastName || ""}`.trim()
      : profile.name || "Student";
    const cgpa = profile.gpa || profile.cgpa || "—";
    const field = profile.preferredProgramCategory || profile.fieldOfStudy || "";

    // State 2
    const $name1 = document.getElementById("profile-name");
    const $cgpa1 = document.getElementById("profile-cgpa");
    const $av1   = document.getElementById("avatar");
    if ($name1) $name1.textContent = name;
    if ($cgpa1) $cgpa1.textContent = cgpa;
    if ($av1)   $av1.textContent = initials(name);

    // State 3
    const $name2 = document.getElementById("profile-name-2");
    const $av2   = document.getElementById("avatar-2");
    const $tagC  = document.getElementById("tag-cgpa");
    const $tagF  = document.getElementById("tag-field");
    if ($name2) $name2.textContent = name;
    if ($av2)   $av2.textContent = initials(name);
    if ($tagC)  $tagC.textContent = `CGPA ${cgpa}`;
    if ($tagF)  {
      $tagF.textContent = field || "—";
      if (!field) $tagF.style.display = "none";
    }
  };

  /* ═══════════════════ BOOT ═══════════════════ */

  async function boot() {
    const { authToken, apiBaseUrl, cachedProfile } = await getStorage([
      "authToken",
      "apiBaseUrl",
      "cachedProfile",
    ]);

    // ── Not logged in ──
    if (!authToken) {
      showState($loggedOut);
      return;
    }

    // ── Logged in — fetch fresh profile (or use cache) ──
    let profile = cachedProfile || null;
    if (apiBaseUrl && authToken) {
      try {
        const res = await fetch(`${apiBaseUrl}/api/extension/profile`, {
          headers: { Authorization: `Bearer ${authToken}` },
        });
        if (res.ok) {
          const json = await res.json();
          profile = json.data || json;
          await setStorage({ cachedProfile: profile });
        } else if (res.status === 401) {
          // Token expired
          await removeStorage(["authToken", "cachedProfile"]);
          showState($loggedOut);
          return;
        }
      } catch {
        // Network error — use cache
      }
    }

    if (profile) fillProfileUI(profile);

    // ── Ask content script for detected fields ──
    const result = await sendToContent("GET_DETECTED_FIELDS");
    const fieldCount = result?.count || 0;

    if (fieldCount > 0) {
      $fieldCount.textContent = fieldCount;
      showState($formState);
    } else {
      showState($noForm);
    }
  }

  /* ═══════════════════ EVENT HANDLERS ═══════════════════ */

  // Login → open webapp
  $btnLogin.addEventListener("click", async () => {
    const { apiBaseUrl } = await getStorage(["apiBaseUrl"]);
    const loginUrl = apiBaseUrl
      ? `${apiBaseUrl.replace(/\/api.*$/, "")}/login`
      : "http://localhost:3000/login";
    chrome.tabs.create({ url: loginUrl });
  });

  // Go to app
  $btnGoApp.addEventListener("click", async () => {
    const { apiBaseUrl } = await getStorage(["apiBaseUrl"]);
    const url = apiBaseUrl
      ? apiBaseUrl.replace(/\/api.*$/, "")
      : "http://localhost:3000";
    chrome.tabs.create({ url: `${url}/student/dashboard` });
  });

  // Logout
  const handleLogout = async () => {
    await removeStorage(["authToken", "cachedProfile"]);
    showState($loggedOut);
  };
  $btnLogout1.addEventListener("click", handleLogout);
  $btnLogout2.addEventListener("click", handleLogout);

  // Re-scan
  $btnRescan.addEventListener("click", async () => {
    $btnRescan.textContent = "Scanning…";
    $btnRescan.disabled = true;

    const result = await sendToContent("RESCAN");
    const count = result?.count || 0;

    if (count > 0) {
      $fieldCount.textContent = count;
      showState($formState);
    } else {
      showState($noForm);
    }

    $btnRescan.textContent = "Re-scan";
    $btnRescan.disabled = false;
  });

  // ── Auto-Fill ──
  $btnFill.addEventListener("click", async () => {
    $btnFill.classList.add("btn-loading");
    $btnFill.innerHTML = `
      <span class="loader" style="width:16px;height:16px;border-width:2px;"></span>
      Filling…`;
    show($fillStatus);
    $progressFill.style.width = "10%";
    $progressText.textContent = "Starting auto-fill…";

    const useAI = $aiToggle.checked;

    // Store AI preference for content.js to read
    await setStorage({ useAiEssays: useAI });

    // Tell content.js to fill
    const result = await sendToContent("FILL_FORM", { useAI });

    // Simulate progress feedback (actual progress comes from content script)
    $progressFill.style.width = "100%";
    $progressText.textContent = result?.status === "filling"
      ? "Review panel open in page ✓"
      : "Done";

    $btnFill.classList.remove("btn-loading");
    $btnFill.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      Filled — Review in Page`;

    // Reset after 4 s
    setTimeout(() => {
      $btnFill.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 20h9"/>
          <path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4 12.5-12.5z"/>
        </svg>
        Auto-Fill Form`;
      hide($fillStatus);
      $progressFill.style.width = "0%";
    }, 4000);
  });

  /* ═══════════════════ INIT ═══════════════════ */
  boot();
})();

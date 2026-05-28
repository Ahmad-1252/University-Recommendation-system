/**
 * UniScout — Chrome Extension Content Script
 * ============================================
 * 1. Detects university application form fields
 * 2. Highlights detected fields (blue outline)
 * 3. Shows floating "Fill with UniScout" button
 * 4. Autofills from user profile via backend API
 * 5. Generates AI content for essay / statement fields
 * 6. Shows "Review & Confirm" panel before finalizing
 */

(() => {
  "use strict";

  /* ═══════════════════════ CONFIG ═══════════════════════ */

  const FIELD_KEYWORDS = [
    "name", "first name", "last name", "full name",
    "email", "e-mail",
    "gpa", "cgpa",
    "statement", "personal statement", "essay",
    "why do you want to join", "describe yourself", "motivation",
    "qualification", "degree",
    "university attended", "institution", "previous university",
    "field of study", "major",
    "phone", "telephone", "mobile",
    "address",
    "nationality", "citizenship",
    "date of birth", "dob", "birth date",
    "country", "program", "course",
    "ielts", "toefl", "budget",
  ];

  /** Keywords that trigger AI essay generation instead of direct fill */
  const ESSAY_KEYWORDS = [
    "statement", "personal statement", "essay",
    "why do you want", "describe yourself", "motivation",
    "cover letter", "letter of intent", "purpose",
  ];

  /** Map detected keyword → profile field(s) */
  const KEYWORD_TO_PROFILE = {
    "first name":           (p) => p.firstName,
    "last name":            (p) => p.lastName,
    "full name":            (p) => `${p.firstName} ${p.lastName}`.trim(),
    "name":                 (p) => `${p.firstName} ${p.lastName}`.trim(),
    "email":                (p) => p.email,
    "e-mail":               (p) => p.email,
    "phone":                (p) => p.phone,
    "telephone":            (p) => p.phone,
    "mobile":               (p) => p.phone,
    "date of birth":        (p) => p.dateOfBirth,
    "dob":                  (p) => p.dateOfBirth,
    "birth date":           (p) => p.dateOfBirth,
    "nationality":          (p) => p.nationality,
    "citizenship":          (p) => p.nationality,
    "address":              (p) => p.address,
    "gpa":                  (p) => p.cgpa?.toString(),
    "cgpa":                 (p) => p.cgpa?.toString(),
    "field of study":       (p) => p.fieldOfStudy,
    "major":                (p) => p.fieldOfStudy,
    "degree":               (p) => p.degreeLevel,
    "qualification":        (p) => p.degreeLevel,
    "university attended":  (p) => p.previousUniversity,
    "institution":          (p) => p.previousUniversity,
    "previous university":  (p) => p.previousUniversity,
    "ielts":                (p) => p.ieltsScore?.toString(),
    "toefl":                (p) => p.ieltsScore?.toString(), // fallback
    "budget":               (p) => p.budget?.toString(),
  };

  const HIGHLIGHT_OUTLINE = "2px solid rgba(59, 130, 246, 0.7)";
  const HIGHLIGHT_COLOR   = "rgba(59, 130, 246, 0.45)";
  const FILLED_OUTLINE    = "2px solid rgba(34, 197, 94, 0.8)";
  const FILLED_COLOR      = "rgba(34, 197, 94, 0.35)";
  const SCAN_DEBOUNCE_MS  = 800;
  const MUTATION_DEBOUNCE_MS = 1200;

  /* ═══════════════════════ STATE ═══════════════════════ */

  let detectedFields = [];      // [{ element, keyword, hint }]
  let filledEntries  = [];      // [{ keyword, hint, value, element, isEssay }]
  let userProfile    = null;
  let floatingBtn    = null;
  let reviewPanel    = null;
  let styleTag       = null;
  let scanTimer      = null;

  /* ═══════════════════════ UTILITIES ═══════════════════════ */

  const norm = (str) =>
    (str || "")
      .replace(/<[^>]*>/g, "")
      .replace(/[_\-]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();

  const matchesKeyword = (text) => {
    const n = norm(text);
    return n ? FIELD_KEYWORDS.find((kw) => n.includes(kw)) || null : null;
  };

  const isEssayField = (keyword) =>
    ESSAY_KEYWORDS.some((ek) => keyword.includes(ek));

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  /* ═══════════════════ CHROME STORAGE HELPERS ═══════════════════ */

  const getStorage = (keys) =>
    new Promise((resolve) => chrome.storage.sync.get(keys, resolve));

  /* ═══════════════════ API HELPERS ═══════════════════ */

  async function fetchProfile() {
    const { apiBaseUrl, authToken } = await getStorage(["apiBaseUrl", "authToken"]);
    if (!apiBaseUrl || !authToken) {
      throw new Error("Missing API URL or auth token. Please sign in via the UniScout popup.");
    }
    const res = await fetch(`${apiBaseUrl}/api/users/profile`, {
      headers: { Authorization: `Bearer ${authToken}`, "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error(`Profile fetch failed (${res.status})`);
    return res.json();
  }

  async function generateEssay(fieldLabel, profile) {
    const { apiBaseUrl, authToken } = await getStorage(["apiBaseUrl", "authToken"]);
    const res = await fetch(`${apiBaseUrl}/api/extension/generate-content`, {
      method: "POST",
      headers: { Authorization: `Bearer ${authToken}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        fieldType: "essay",
        userProfile: profile,
        fieldLabel,
      }),
    });
    if (!res.ok) throw new Error(`Essay generation failed (${res.status})`);
    const data = await res.json();
    return data.generatedText;
  }

  /* ═══════════════════ LABEL / HINT RESOLUTION ═══════════════════ */

  const getFieldHints = (el) => {
    const hints = [];

    if (el.placeholder) hints.push(el.placeholder);
    if (el.name) hints.push(el.name);
    if (el.id) hints.push(el.id);
    if (el.getAttribute("aria-label")) hints.push(el.getAttribute("aria-label"));

    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      labelledBy.split(/\s+/).forEach((refId) => {
        const ref = document.getElementById(refId);
        if (ref) hints.push(ref.textContent);
      });
    }

    if (el.id) {
      document.querySelectorAll(`label[for="${CSS.escape(el.id)}"]`).forEach((lbl) =>
        hints.push(lbl.textContent)
      );
    }

    const ancestorLabel = el.closest("label");
    if (ancestorLabel) hints.push(ancestorLabel.textContent);

    const prev = el.previousElementSibling;
    if (prev && ["SPAN", "DIV", "P", "LABEL", "STRONG", "B"].includes(prev.tagName))
      hints.push(prev.textContent);

    const parent = el.parentElement;
    if (parent) {
      const clone = parent.cloneNode(true);
      clone.querySelectorAll("input, textarea, select").forEach((c) => c.remove());
      const t = clone.textContent.trim();
      if (t.length > 0 && t.length < 120) hints.push(t);
    }

    return hints;
  };

  /* ═══════════════════ FIELD DETECTION ═══════════════════ */

  const getAllInputElements = () => [
    ...document.querySelectorAll(
      'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"]):not([type="image"]), ' +
      "textarea, select, " +
      '[contenteditable="true"], [role="textbox"], [role="combobox"]'
    ),
  ];

  const scanForFormFields = () => {
    const inputs = getAllInputElements();
    const matches = [];
    inputs.forEach((el) => {
      if (el.offsetParent === null && getComputedStyle(el).position !== "fixed") return;
      const hints = getFieldHints(el);
      for (const hint of hints) {
        const kw = FIELD_KEYWORDS.find((k) => norm(hint).includes(k));
        if (kw) {
          matches.push({ element: el, keyword: kw, hint: norm(hint) });
          break;
        }
      }
    });
    return matches;
  };

  /* ═══════════════════ SET FIELD VALUE ═══════════════════ */

  /**
   * Set value on a form element in a way that works with
   * React / Angular (triggers change & input events).
   */
  const setFieldValue = (el, value) => {
    if (!value) return;

    if (el.getAttribute("contenteditable") === "true" || el.getAttribute("role") === "textbox") {
      el.textContent = value;
    } else {
      // React stores value via internal state; we need the native setter
      const nativeSet = Object.getOwnPropertyDescriptor(
        el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
        "value"
      )?.set;

      if (nativeSet) {
        nativeSet.call(el, value);
      } else {
        el.value = value;
      }
    }

    // Dispatch events so frameworks pick up the change
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
  };

  /* ═══════════════════ STYLES ═══════════════════ */

  const injectStyles = () => {
    if (styleTag) return;
    styleTag = document.createElement("style");
    styleTag.id = "uniscout-ext-styles";
    styleTag.textContent = `
      /* ---- Detection highlight (blue) ---- */
      .uniscout-highlight {
        outline: ${HIGHLIGHT_OUTLINE} !important;
        box-shadow: 0 0 0 3px ${HIGHLIGHT_COLOR} !important;
        transition: box-shadow .25s ease, outline .25s ease;
      }

      /* ---- Filled highlight (green) ---- */
      .uniscout-filled {
        outline: ${FILLED_OUTLINE} !important;
        box-shadow: 0 0 0 3px ${FILLED_COLOR} !important;
      }

      /* ---- Floating Action Button ---- */
      #uniscout-fab {
        position: fixed; bottom: 28px; right: 28px; z-index: 2147483647;
        display: flex; align-items: center; gap: 10px;
        padding: 12px 22px; border: none; border-radius: 50px;
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #fff;
        font: 600 15px/1 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        cursor: pointer;
        box-shadow: 0 6px 24px rgba(37,99,235,.45), 0 2px 6px rgba(0,0,0,.18);
        transition: transform .2s, box-shadow .2s;
        user-select: none;
      }
      #uniscout-fab:hover { transform: translateY(-2px) scale(1.03);
        box-shadow: 0 8px 30px rgba(37,99,235,.55), 0 3px 8px rgba(0,0,0,.22); }
      #uniscout-fab:active { transform: scale(.97); }
      #uniscout-fab svg { width: 20px; height: 20px; flex-shrink: 0; }
      #uniscout-fab .badge {
        background: rgba(255,255,255,.2); border-radius: 10px;
        padding: 2px 8px; font-size: 12px; font-weight: 700;
      }

      /* ---- Spinner on FAB ---- */
      #uniscout-fab.loading { pointer-events: none; opacity: .75; }
      @keyframes uniscout-spin { to { transform: rotate(360deg); } }
      .uniscout-spinner {
        width: 18px; height: 18px; border: 2px solid rgba(255,255,255,.3);
        border-top-color: #fff; border-radius: 50%;
        animation: uniscout-spin .6s linear infinite;
      }

      /* ---- "No form" badge ---- */
      #uniscout-badge {
        position: fixed; bottom: 28px; right: 28px; z-index: 2147483647;
        padding: 10px 18px; border-radius: 12px;
        background: #1e293b; color: #94a3b8;
        font: 500 13px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        box-shadow: 0 4px 16px rgba(0,0,0,.25);
        pointer-events: none; opacity: 0; transform: translateY(8px);
        animation: uniscout-fade-in .4s ease .3s forwards;
      }
      @keyframes uniscout-fade-in { to { opacity:1; transform:translateY(0); } }

      /* ---- Review Panel ---- */
      #uniscout-review {
        position: fixed; bottom: 90px; right: 28px; z-index: 2147483647;
        width: 400px; max-height: 70vh; overflow-y: auto;
        background: #fff; border-radius: 16px;
        box-shadow: 0 12px 48px rgba(0,0,0,.18), 0 2px 8px rgba(0,0,0,.1);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        border: 1px solid #e2e8f0;
      }
      #uniscout-review .header {
        padding: 16px 20px; border-bottom: 1px solid #e2e8f0;
        display: flex; justify-content: space-between; align-items: center;
      }
      #uniscout-review .header h3 {
        margin: 0; font-size: 16px; font-weight: 700; color: #0f172a;
      }
      #uniscout-review .header .close-btn {
        background: none; border: none; font-size: 20px; cursor: pointer;
        color: #94a3b8; line-height: 1;
      }
      #uniscout-review .body { padding: 12px 20px; }
      #uniscout-review .field-row {
        padding: 10px 0; border-bottom: 1px solid #f1f5f9;
        display: flex; flex-direction: column; gap: 4px;
      }
      #uniscout-review .field-row:last-child { border-bottom: none; }
      #uniscout-review .field-label {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: .5px; color: #64748b;
      }
      #uniscout-review .field-value {
        font-size: 14px; color: #1e293b; word-break: break-word;
        max-height: 80px; overflow-y: auto;
      }
      #uniscout-review .field-tag {
        display: inline-block; font-size: 10px; font-weight: 600;
        padding: 2px 6px; border-radius: 4px; margin-top: 2px; width: fit-content;
      }
      #uniscout-review .tag-profile { background: #dbeafe; color: #1d4ed8; }
      #uniscout-review .tag-ai      { background: #fae8ff; color: #a21caf; }
      #uniscout-review .footer {
        padding: 14px 20px; border-top: 1px solid #e2e8f0;
        display: flex; gap: 10px; justify-content: flex-end;
      }
      #uniscout-review .btn {
        padding: 8px 18px; border-radius: 8px; border: none;
        font-size: 14px; font-weight: 600; cursor: pointer; transition: background .15s;
      }
      #uniscout-review .btn-cancel {
        background: #f1f5f9; color: #475569;
      }
      #uniscout-review .btn-cancel:hover { background: #e2e8f0; }
      #uniscout-review .btn-confirm {
        background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff;
      }
      #uniscout-review .btn-confirm:hover { background: #16a34a; }

      /* ---- Toast ---- */
      .uniscout-toast {
        position: fixed; top: 24px; right: 28px; z-index: 2147483647;
        padding: 12px 20px; border-radius: 10px;
        font: 500 14px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        box-shadow: 0 4px 20px rgba(0,0,0,.15);
        opacity: 0; transform: translateY(-8px);
        animation: uniscout-fade-in .3s ease forwards;
      }
      .uniscout-toast.success { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
      .uniscout-toast.error   { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
    `;
    document.head.appendChild(styleTag);
  };

  /* ═══════════════════ TOAST HELPER ═══════════════════ */

  const showToast = (message, type = "success", duration = 3500) => {
    const t = document.createElement("div");
    t.className = `uniscout-toast ${type}`;
    t.textContent = message;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), duration);
  };

  /* ═══════════════════ HIGHLIGHT HELPERS ═══════════════════ */

  const highlightFields = (fields) => {
    document.querySelectorAll(".uniscout-highlight").forEach((e) =>
      e.classList.remove("uniscout-highlight")
    );
    fields.forEach(({ element }) => element.classList.add("uniscout-highlight"));
  };

  const markFilled = (el) => {
    el.classList.remove("uniscout-highlight");
    el.classList.add("uniscout-filled");
  };

  /* ═══════════════════ FLOATING BUTTON ═══════════════════ */

  const removeFloatingUI = () => {
    floatingBtn?.remove(); floatingBtn = null;
    document.getElementById("uniscout-badge")?.remove();
  };

  const showFAB = (fieldCount) => {
    removeFloatingUI();
    const btn = document.createElement("button");
    btn.id = "uniscout-fab";
    btn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4 12.5-12.5z"/>
      </svg>
      Fill with UniScout
      <span class="badge">${fieldCount}</span>`;
    btn.addEventListener("click", handleAutofill);
    document.body.appendChild(btn);
    floatingBtn = btn;
  };

  const setFABLoading = (loading) => {
    if (!floatingBtn) return;
    if (loading) {
      floatingBtn.classList.add("loading");
      floatingBtn.innerHTML = `<div class="uniscout-spinner"></div> Filling fields…`;
    } else {
      floatingBtn.classList.remove("loading");
    }
  };

  const showNoBadge = () => {
    removeFloatingUI();
    const badge = document.createElement("div");
    badge.id = "uniscout-badge";
    badge.textContent = "No form detected on this page";
    document.body.appendChild(badge);
    setTimeout(() => badge.remove(), 4000);
  };

  /* ═══════════════════ REVIEW PANEL ═══════════════════ */

  const showReviewPanel = (entries) => {
    reviewPanel?.remove();

    const panel = document.createElement("div");
    panel.id = "uniscout-review";

    const rows = entries.map((e) => {
      const truncated = e.value.length > 200 ? e.value.slice(0, 200) + "…" : e.value;
      const tag = e.isEssay
        ? `<span class="field-tag tag-ai">AI Generated</span>`
        : `<span class="field-tag tag-profile">From Profile</span>`;
      return `
        <div class="field-row">
          <div class="field-label">${escapeHtml(e.keyword)}</div>
          <div class="field-value">${escapeHtml(truncated)}</div>
          ${tag}
        </div>`;
    }).join("");

    panel.innerHTML = `
      <div class="header">
        <h3>Review Filled Fields (${entries.length})</h3>
        <button class="close-btn" id="uniscout-review-close">&times;</button>
      </div>
      <div class="body">${rows}</div>
      <div class="footer">
        <button class="btn btn-cancel" id="uniscout-review-cancel">Undo All</button>
        <button class="btn btn-confirm" id="uniscout-review-confirm">✓ Confirm</button>
      </div>`;

    document.body.appendChild(panel);
    reviewPanel = panel;

    // Close
    panel.querySelector("#uniscout-review-close").addEventListener("click", () => {
      undoAll(entries);
      panel.remove();
      reviewPanel = null;
    });

    // Cancel → undo all fills
    panel.querySelector("#uniscout-review-cancel").addEventListener("click", () => {
      undoAll(entries);
      panel.remove();
      reviewPanel = null;
      showToast("Autofill undone", "error");
    });

    // Confirm → keep values, close panel
    panel.querySelector("#uniscout-review-confirm").addEventListener("click", () => {
      panel.remove();
      reviewPanel = null;
      showToast(`${entries.length} fields confirmed ✓`, "success");
    });
  };

  const undoAll = (entries) => {
    entries.forEach(({ element }) => {
      setFieldValue(element, "");
      element.classList.remove("uniscout-filled");
      element.classList.add("uniscout-highlight");
    });
    filledEntries = [];
  };

  const escapeHtml = (str) =>
    str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  /* ═══════════════════ AUTOFILL ORCHESTRATOR ═══════════════════ */

  async function handleAutofill() {
    if (detectedFields.length === 0) return;

    setFABLoading(true);
    filledEntries = [];

    try {
      // 1. Fetch user profile
      userProfile = await fetchProfile();

      // 2. Iterate detected fields
      for (const field of detectedFields) {
        const { element, keyword, hint } = field;

        try {
          if (isEssayField(keyword)) {
            // ─── AI Essay / Statement Generation ───
            const label = hint || keyword;
            const generated = await generateEssay(label, userProfile);
            if (generated) {
              setFieldValue(element, generated);
              markFilled(element);
              filledEntries.push({ keyword, hint, value: generated, element, isEssay: true });
            }
          } else {
            // ─── Direct Profile Fill ───
            const resolver = findResolver(keyword);
            const value = resolver ? resolver(userProfile) : null;
            if (value) {
              setFieldValue(element, value);
              markFilled(element);
              filledEntries.push({ keyword, hint, value, element, isEssay: false });
            }
          }
        } catch (fieldErr) {
          console.warn(`[UniScout] Failed to fill "${keyword}":`, fieldErr);
        }

        // Small stagger so the UI doesn't freeze
        await sleep(50);
      }

      // 3. Show Review Panel
      if (filledEntries.length > 0) {
        showReviewPanel(filledEntries);
        showToast(`Filled ${filledEntries.length} fields — please review`, "success");
      } else {
        showToast("No matching profile data found", "error");
      }
    } catch (err) {
      console.error("[UniScout] Autofill error:", err);
      showToast(err.message || "Autofill failed", "error");
    } finally {
      setFABLoading(false);
      // Rebuild the FAB to its normal state
      if (detectedFields.length > 0) showFAB(detectedFields.length);
    }
  }

  /**
   * Find the best profile resolver for a keyword.
   * Tries exact match first, then partial match.
   */
  const findResolver = (keyword) => {
    if (KEYWORD_TO_PROFILE[keyword]) return KEYWORD_TO_PROFILE[keyword];
    for (const [key, fn] of Object.entries(KEYWORD_TO_PROFILE)) {
      if (keyword.includes(key) || key.includes(keyword)) return fn;
    }
    return null;
  };

  /* ═══════════════════ MAIN SCAN ═══════════════════ */

  const runScan = () => {
    injectStyles();
    const fields = scanForFormFields();
    detectedFields = fields;

    if (fields.length > 0) {
      highlightFields(fields);
      showFAB(fields.length);
      chrome.storage?.local?.set({
        uniscout_detected: fields.map(({ keyword, hint }) => ({ keyword, hint })),
      });
      console.log(
        `%c[UniScout] Detected ${fields.length} field(s)`,
        "color:#2563eb;font-weight:bold",
        fields.map((f) => f.keyword)
      );
    } else {
      showNoBadge();
      chrome.storage?.local?.set({ uniscout_detected: [] });
    }
  };

  /* ═══════════════════ LIFECYCLE ═══════════════════ */

  const debouncedScan = () => {
    clearTimeout(scanTimer);
    scanTimer = setTimeout(runScan, SCAN_DEBOUNCE_MS);
  };

  // Initial scan
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", debouncedScan);
  } else {
    debouncedScan();
  }

  // Re-scan on DOM mutations (SPA support)
  let mutationTimer = null;
  new MutationObserver(() => {
    clearTimeout(mutationTimer);
    mutationTimer = setTimeout(runScan, MUTATION_DEBOUNCE_MS);
  }).observe(document.documentElement, { childList: true, subtree: true });

  // URL change detection (SPA soft navigation)
  let lastUrl = location.href;
  setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      debouncedScan();
    }
  }, 1500);

  /* ═══════════════════ MESSAGE LISTENER ═══════════════════ */

  chrome.runtime?.onMessage?.addListener((msg, _sender, sendResponse) => {
    if (msg.action === "GET_DETECTED_FIELDS") {
      sendResponse({
        fields: detectedFields.map(({ keyword, hint }) => ({ keyword, hint })),
        count: detectedFields.length,
      });
    }
    if (msg.action === "RESCAN") {
      runScan();
      sendResponse({ status: "rescanned", count: detectedFields.length });
    }
    if (msg.action === "FILL_FORM") {
      handleAutofill();
      sendResponse({ status: "filling" });
    }
    return true;
  });
})();

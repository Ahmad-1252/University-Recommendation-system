# UniScout Chrome Extension — Manual Test Checklist

> **Tester:** ********\_******** **Date:** ********\_********
> **Extension Version:** 2.1.0 **Backend URL:** `http://localhost:3003`

Legend: ✅ Pass | ❌ Fail | ⚠️ Partial | N/A

---

## 1. Installation & Setup

| #   | Test                                                                               | Expected                                                       | Result |
| --- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------ |
| 1.1 | Load unpacked extension via `chrome://extensions` → Developer Mode → Load Unpacked | Extension appears with UniScout name, icon, and no errors      | ☐      |
| 1.2 | Check service worker status in `chrome://extensions`                               | Shows "Service worker (active)" — no error badge               | ☐      |
| 1.3 | Click extension icon in toolbar                                                    | Popup opens at 360px width, shows loading → logged-out state   | ☐      |
| 1.4 | Open any website, right-click → Inspect → Console                                  | No `[UniScout]` errors logged on a generic page                | ☐      |
| 1.5 | First install opens login page                                                     | `http://localhost:3000/login` opens in a new tab automatically | ☐      |

---

## 2. Authentication Flow

### 2a. Login

| #   | Test                               | Expected                                                                                                | Result |
| --- | ---------------------------------- | ------------------------------------------------------------------------------------------------------- | ------ |
| 2.1 | Click "Login to UniScout" in popup | New tab opens to webapp login page                                                                      | ☐      |
| 2.2 | Log in on the webapp               | Token should sync to extension (check via `chrome.storage.sync.get("authToken")` in background console) | ☐      |
| 2.3 | Re-open popup after login          | Shows logged-in state (profile name, CGPA visible)                                                      | ☐      |

### 2b. Token Validation

| #   | Test                                                                                                                 | Expected                                                      | Result |
| --- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | ------ |
| 2.4 | **Valid token:** Open popup normally                                                                                 | Profile loads, name and CGPA shown correctly                  | ☐      |
| 2.5 | **Missing token:** Manually clear token via `chrome.storage.sync.remove("authToken")`, re-open popup                 | Shows logged-out state with login button                      | ☐      |
| 2.6 | **Expired token:** Set a garbage value via `chrome.storage.sync.set({authToken: "expired.jwt.here"})`, re-open popup | API returns 401 → popup clears token → shows logged-out state | ☐      |

### 2c. Logout

| #   | Test                             | Expected                                          | Result |
| --- | -------------------------------- | ------------------------------------------------- | ------ |
| 2.7 | Click "Sign out" button in popup | Token cleared, popup switches to logged-out state | ☐      |
| 2.8 | Re-open popup after logout       | Still shows logged-out state (not cached profile) | ☐      |

---

## 3. Form Detection

Test on 3 different form structures. Navigate to each page while logged in.

### 3a. Standard HTML Form

> **Test page:** Any university application page with `<form>`, `<input>`, `<textarea>` elements.
> **Fallback:** Create a local `test-form.html` with labeled inputs for name, email, GPA, statement.

| #   | Test                      | Expected                                                                | Result |
| --- | ------------------------- | ----------------------------------------------------------------------- | ------ |
| 3.1 | Navigate to the test page | Blue highlight outlines appear on matching fields                       | ☐      |
| 3.2 | Check floating button     | "Fill with UniScout" FAB appears at bottom-right with field count badge | ☐      |
| 3.3 | Open popup                | Shows "X fields detected on this page"                                  | ☐      |

### 3b. React/Angular SPA Form

> **Test page:** Any SPA with `div`-based form inputs (e.g., a Material UI or Ant Design form).

| #   | Test                                      | Expected                                                                            | Result |
| --- | ----------------------------------------- | ----------------------------------------------------------------------------------- | ------ |
| 3.4 | Navigate to SPA form page                 | Fields with matching `aria-label`, `placeholder`, or `name` attributes are detected | ☐      |
| 3.5 | SPA navigation (without full page reload) | MutationObserver triggers re-scan → new fields detected                             | ☐      |

### 3c. Mixed / Contenteditable

> **Test page:** A page with `contenteditable="true"` divs or `role="textbox"`.

| #   | Test                                    | Expected                                                    | Result |
| --- | --------------------------------------- | ----------------------------------------------------------- | ------ |
| 3.6 | Navigate to page with rich-text editors | Contenteditable regions with essay-like labels are detected | ☐      |

---

## 4. Profile Fetch

| #   | Test                                                       | Expected                                              | Result |
| --- | ---------------------------------------------------------- | ----------------------------------------------------- | ------ |
| 4.1 | **Valid token + server running:** Open popup               | Profile card shows correct name, CGPA, field of study | ☐      |
| 4.2 | **Valid token + server down:** Stop backend, open popup    | Uses cached profile (or shows graceful error)         | ☐      |
| 4.3 | **Profile with missing fields:** User has no phone/GPA set | Popup displays "—" for missing fields, no crash       | ☐      |

---

## 5. Autofill Accuracy

> Perform these on the test form from section 3a.

| #   | Field                  | Source                             | Expected Value        | Matches? |
| --- | ---------------------- | ---------------------------------- | --------------------- | -------- |
| 5.1 | First Name / Full Name | Profile `firstName + lastName`     | User's actual name    | ☐        |
| 5.2 | Email                  | Profile `email`                    | User's actual email   | ☐        |
| 5.3 | Phone                  | Profile `phone`                    | User's phone or empty | ☐        |
| 5.4 | GPA / CGPA             | Profile `gpa`                      | Numeric GPA value     | ☐        |
| 5.5 | Date of Birth          | Profile `dateOfBirth`              | Date string           | ☐        |
| 5.6 | Nationality            | Profile `location` / `nationality` | Correct value         | ☐        |
| 5.7 | Field of Study         | Profile `preferredProgramCategory` | Correct value         | ☐        |
| 5.8 | Degree Level           | Profile `preferredDegreeLevel`     | Correct value         | ☐        |
| 5.9 | Previous University    | Profile `education`                | Correct value         | ☐        |

### Post-fill checks

| #    | Test                                 | Expected                                                                                     | Result |
| ---- | ------------------------------------ | -------------------------------------------------------------------------------------------- | ------ |
| 5.10 | All filled fields have green outline | `.uniscout-filled` class applied, green glow visible                                         | ☐      |
| 5.11 | React `onChange` fires               | If testing on a React form, check that React state updated (field shows value, not just DOM) | ☐      |

---

## 6. AI Essay Generation

> Requires: Backend running with `OPENAI_API_KEY` or `GROQ_API_KEY` in `.env`.

| #   | Test                                                     | Expected                                           | Result |
| --- | -------------------------------------------------------- | -------------------------------------------------- | ------ |
| 6.1 | Form has a "Personal Statement" textarea                 | AI generates 150–300 word text, fills the field    | ☐      |
| 6.2 | Generated text is first-person                           | Reads as "I studied…" not "The student studied…"   | ☐      |
| 6.3 | Generated text avoids banned phrases                     | No "I am thrilled", "passionate about", "eager to" | ☐      |
| 6.4 | Generated text includes profile data                     | Mentions user's GPA, university, or field of study | ☐      |
| 6.5 | "Short answer" field                                     | AI generates 50–100 words (shorter than statement) | ☐      |
| 6.6 | Toggle "Use AI for essay fields" OFF in popup, then fill | Essay fields are skipped (left empty)              | ☐      |
| 6.7 | **Rate limit:** Generate 11 times in 24h                 | 11th request returns 429 "Daily limit reached"     | ☐      |
| 6.8 | **No API key:** Remove keys from `.env`, restart server  | Returns 503 "AI generation not configured"         | ☐      |

---

## 7. Review Panel

| #   | Test                                      | Expected                                                               | Result |
| --- | ----------------------------------------- | ---------------------------------------------------------------------- | ------ |
| 7.1 | After auto-fill completes                 | Review panel appears at bottom-right of the page                       | ☐      |
| 7.2 | Panel shows correct field count           | Header says "Review Filled Fields (N)" matching actual fills           | ☐      |
| 7.3 | Each row shows field label + filled value | Values match what was inserted into the form                           | ☐      |
| 7.4 | Profile fields tagged "From Profile"      | Blue tag on name, email, GPA rows                                      | ☐      |
| 7.5 | AI fields tagged "AI Generated"           | Purple tag on essay/statement rows                                     | ☐      |
| 7.6 | Click **✓ Confirm**                       | Panel closes, green highlights remain, toast "N fields confirmed ✓"    | ☐      |
| 7.7 | Click **Undo All**                        | All fields cleared, highlights revert to blue, toast "Autofill undone" | ☐      |
| 7.8 | Click **✕ (close button)**                | Same as Undo All — fields cleared, panel closes                        | ☐      |

---

## 8. Edge Cases

| #    | Test                                                                 | Expected                                                                | Result |
| ---- | -------------------------------------------------------------------- | ----------------------------------------------------------------------- | ------ |
| 8.1  | **No forms on page** (e.g., google.com)                              | "No form detected" toast appears briefly, disappears after 4s           | ☐      |
| 8.2  | **Popup on no-form page**                                            | Popup shows STATE 2: "No application form detected"                     | ☐      |
| 8.3  | **Multiple forms on same page**                                      | All matching fields across all forms are detected and highlighted       | ☐      |
| 8.4  | **SPA navigation** (click a link that changes URL without reload)    | URL change poller triggers re-scan within ~1.5s                         | ☐      |
| 8.5  | **Dynamic form load** (form injected via JavaScript after page load) | MutationObserver detects new fields within ~1.2s                        | ☐      |
| 8.6  | **Hidden fields** (`type="hidden"`, `display:none`)                  | NOT detected — only visible, interactable fields                        | ☐      |
| 8.7  | **iframe-embedded form**                                             | Content script does NOT run in iframes (expected limitation — document) | ☐      |
| 8.8  | **Re-scan button in popup**                                          | Click "Re-scan" → updates field count, changes state if needed          | ☐      |
| 8.9  | **Double-click "Auto-Fill"**                                         | Button goes into loading state → prevents double execution              | ☐      |
| 8.10 | **Very long essay response**                                         | Review panel truncates to 200 chars with "…", scrollable                | ☐      |

---

## Test Form Template

Save this as `test-form.html` and open it locally to test against:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Test University Application</title>
  </head>
  <body style="max-width:600px;margin:40px auto;font-family:sans-serif">
    <h1>University Application Form</h1>
    <form>
      <label
        >Full Name<br /><input
          type="text"
          name="full_name"
          placeholder="Your full name" /></label
      ><br /><br />
      <label
        >Email Address<br /><input
          type="email"
          name="email"
          placeholder="Email" /></label
      ><br /><br />
      <label
        >Phone Number<br /><input
          type="tel"
          name="phone"
          placeholder="Phone" /></label
      ><br /><br />
      <label>Date of Birth<br /><input type="date" name="dob" /></label
      ><br /><br />
      <label
        >Nationality<br /><input
          type="text"
          name="nationality"
          placeholder="Nationality" /></label
      ><br /><br />
      <label
        >CGPA<br /><input
          type="number"
          name="cgpa"
          step="0.01"
          placeholder="CGPA" /></label
      ><br /><br />
      <label
        >Field of Study<br /><input
          type="text"
          name="field_of_study"
          placeholder="Field of study" /></label
      ><br /><br />
      <label
        >Degree Level<br /><input
          type="text"
          name="degree"
          placeholder="Degree level" /></label
      ><br /><br />
      <label
        >Previous University<br /><input
          type="text"
          name="university_attended"
          placeholder="University attended" /></label
      ><br /><br />
      <label
        >Personal Statement<br /><textarea
          name="personal_statement"
          rows="6"
          placeholder="Why do you want to join this program?"
        ></textarea></label
      ><br /><br />
      <label
        >Short Answer<br /><textarea
          name="short_answer"
          rows="3"
          placeholder="Describe yourself in a few sentences"
        ></textarea></label
      ><br /><br />
      <button type="submit">Submit</button>
    </form>
  </body>
</html>
```

---

## Summary

| Category             | Total Tests | Passed | Failed |
| -------------------- | ----------- | ------ | ------ |
| 1. Installation      | 5           |        |        |
| 2. Authentication    | 8           |        |        |
| 3. Form Detection    | 6           |        |        |
| 4. Profile Fetch     | 3           |        |        |
| 5. Autofill Accuracy | 11          |        |        |
| 6. AI Generation     | 8           |        |        |
| 7. Review Panel      | 8           |        |        |
| 8. Edge Cases        | 10          |        |        |
| **TOTAL**            | **59**      |        |        |

**Overall Result:** ☐ PASS / ☐ FAIL

**Notes:**

---

---

---

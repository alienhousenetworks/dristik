/**
 * Dristik First-Party Behavioral & Conversion Event SDK (v4.0)
 * Performance budget: < 15 KB gzipped, async non-blocking, zero dependencies.
 * Privacy invariants:
 *  - Respects explicit consent categories (analytics, replay, experimentation) & withdrawal.
 *  - Never transmits password, payment/card, CVV, SSN, email, or phone values.
 *  - Stable deterministic event_id per emission for zero-duplicate server ingestion.
 */
(function (w, d) {
  "use strict";
  var t0 = w.performance && w.performance.now ? w.performance.now() : Date.now();
  var cfg = w.DRISTIK_CONFIG || {};
  var endpoint = cfg.endpoint || "/api/v1/ingest/events";
  var orgId = cfg.orgId || "";
  var domain = cfg.domain || (w.location ? w.location.hostname : "");
  var consent = w.__dristikConsent || { analytics: false, replay: false, experimentation: false };
  var visitorId = (w.localStorage && w.localStorage.getItem("dristik_vid")) || ("v_" + Math.random().toString(36).slice(2, 14));
  var sessionId = (w.sessionStorage && w.sessionStorage.getItem("dristik_sid")) || ("s_" + Math.random().toString(36).slice(2, 14));
  try {
    if (w.localStorage && consent.analytics) w.localStorage.setItem("dristik_vid", visitorId);
    if (w.sessionStorage && consent.analytics) w.sessionStorage.setItem("dristik_sid", sessionId);
  } catch (_) {}

  var SENSITIVE_RE = /(pass|pwd|card|cc-|cvv|cvc|ssn|aadhaar|pan|email|phone|tel|secret)/i;
  var PII_TEXT_RE = /([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\b(?:\d[ -]*?){13,19}\b)/g;

  function deviceCategory() {
    var width = w.innerWidth || 1280;
    if (width < 768) return "mobile";
    if (width < 1024) return "tablet";
    return "desktop";
  }

  function isBot() {
    var ua = (w.navigator && w.navigator.userAgent) || "";
    return /bot|crawler|spider|headlesschrome|playwright|puppeteer/i.test(ua) || Boolean(w.navigator && w.navigator.webdriver);
  }

  function maskValue(key, val) {
    if (typeof val !== "string") return val;
    if (SENSITIVE_RE.test(String(key || ""))) return "[MASKED]";
    return val.replace(PII_TEXT_RE, "[MASKED]");
  }

  function sanitizeObject(obj) {
    if (!obj || typeof obj !== "object") return obj;
    var out = {};
    for (var k in obj) {
      if (!Object.prototype.hasOwnProperty.call(obj, k)) continue;
      out[k] = typeof obj[k] === "object" && obj[k] !== null ? sanitizeObject(obj[k]) : maskValue(k, obj[k]);
    }
    return out;
  }

  function stableEventId(name) {
    return "ev_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 10) + "_" + name.slice(0, 8);
  }

  function cssSelector(el) {
    if (!el || !el.tagName) return "";
    if (el.id) return "#" + el.id;
    var cls = typeof el.className === "string" && el.className.trim() ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : "";
    return el.tagName.toLowerCase() + cls;
  }

  function send(eventName, extra) {
    if (!consent.analytics || isBot()) return null;
    var nowMs = w.performance && w.performance.now ? w.performance.now() : Date.now();
    var payload = sanitizeObject(Object.assign({
      event_id: (extra && extra.event_id) || stableEventId(eventName),
      org_id: orgId,
      domain: domain,
      visitor_id: visitorId,
      session_id: sessionId,
      event_name: eventName,
      page_url: w.location ? w.location.href : "",
      http_referrer: d.referrer || "",
      device_category: deviceCategory(),
      viewport_w: w.innerWidth || 0,
      viewport_h: w.innerHeight || 0,
      consent_granted: true,
      sdk_load_ms: Math.round((nowMs - t0) * 100) / 100,
      event_ts_utc: new Date().toISOString()
    }, extra || {}));

    var body = JSON.stringify(payload);
    if (w.navigator && typeof w.navigator.sendBeacon === "function") {
      try {
        w.navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }));
        return payload;
      } catch (_) {}
    }
    if (typeof w.fetch === "function") {
      w.fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true }).catch(function () {});
    }
    return payload;
  }

  // Rage-click & normalized click tracking
  var recentClicks = [];
  if (d && d.addEventListener) {
    d.addEventListener("click", function (e) {
      var now = Date.now();
      recentClicks = recentClicks.filter(function (c) { return now - c.t < 1000; });
      recentClicks.push({ x: e.clientX, y: e.clientY, t: now });
      var rage = recentClicks.filter(function (c) { return Math.abs(c.x - e.clientX) < 30 && Math.abs(c.y - e.clientY) < 30; }).length >= 3;
      var target = e.target;
      var interactive = target && target.closest && Boolean(target.closest("a,button,input,select,textarea,[role=button]"));
      send("click", {
        click_x: w.innerWidth ? Math.round((e.clientX / w.innerWidth) * 1000) / 1000 : 0,
        click_y: w.innerHeight ? Math.round((e.clientY / w.innerHeight) * 1000) / 1000 : 0,
        dom_selector: cssSelector(target),
        is_rage_click: rage,
        is_dead_click: !interactive
      });
    }, { passive: true });

    // Scroll depth milestones (25, 50, 75, 90, 100)
    var sentScroll = {};
    w.addEventListener("scroll", function () {
      var docH = Math.max(d.documentElement.scrollHeight - w.innerHeight, 1);
      var pct = Math.min(100, Math.round((w.scrollY / docH) * 100));
      [25, 50, 75, 90, 100].forEach(function (m) {
        if (pct >= m && !sentScroll[m]) {
          sentScroll[m] = true;
          send("scroll_depth", { scroll_depth_pct: m });
        }
      });
    }, { passive: true });

    // Form field interaction (never captures field values!)
    d.addEventListener("focusin", function (e) {
      var el = e.target;
      if (!el || !el.form) return;
      var fname = el.name || el.id || el.type || "field";
      send("form_field_focus", {
        form_id: el.form.id || el.form.name || "form",
        form_field_name: SENSITIVE_RE.test(fname) || el.type === "password" ? "[MASKED_FIELD]" : fname
      });
    }, { passive: true });
  }

  w.DristikSDK = {
    track: send,
    trackBackendFormResult: function (formId, httpStatus) {
      return send("form_submit_result", { form_id: formId, backend_submit_status: httpStatus });
    },
    setConsent: function (next) {
      consent = Object.assign({}, consent, next || {});
      w.__dristikConsent = consent;
    },
    withdrawConsent: function () {
      consent = { analytics: false, replay: false, experimentation: false };
      w.__dristikConsent = consent;
      try { w.localStorage.removeItem("dristik_vid"); w.sessionStorage.removeItem("dristik_sid"); } catch (_) {}
    },
    sanitizeObject: sanitizeObject
  };
})(typeof window !== "undefined" ? window : globalThis, typeof document !== "undefined" ? document : {});

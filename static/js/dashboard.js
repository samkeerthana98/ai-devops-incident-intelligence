/* AI DevOps Incident Intelligence — Dashboard JS
   Minimal vanilla JavaScript. No frameworks or external dependencies.
*/

(function () {
  "use strict";

  // DOM elements
  var form = document.getElementById("incident-form");
  var createBtn = document.getElementById("create-btn");
  var createError = document.getElementById("create-error");
  var createSuccess = document.getElementById("create-success");
  var incidentsList = document.getElementById("incidents-list");
  var incidentCount = document.getElementById("incident-count");
  var noIncidents = document.getElementById("no-incidents");
  var analysisSection = document.getElementById("analysis-section");
  var analysisError = document.getElementById("analysis-error");
  var closeAnalysis = document.getElementById("close-analysis");

  // Analysis display elements
  var aSummary = document.getElementById("analysis-summary");
  var aCause = document.getElementById("analysis-likely-cause");
  var aEvidence = document.getElementById("analysis-evidence");
  var aRecs = document.getElementById("analysis-recommendations");
  var aSources = document.getElementById("analysis-runbook-sources");

  // ---------------------------------------------------------------------------
  // Utility helpers
  // ---------------------------------------------------------------------------

  function show(el) { if (el) el.hidden = false; }
  function hide(el) { if (el) el.hidden = true; }
  function setError(el, msg) { if (el) { el.textContent = msg; show(el); } }
  function clearMsg(el) { if (el) { el.textContent = ""; hide(el); } }

  function escapeHtml(str) {
    if (!str) return "";
    var div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------------------------------------------------------------------------
  // Incident creation
  // ---------------------------------------------------------------------------

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    clearMsg(createError);
    clearMsg(createSuccess);
    createBtn.disabled = true;
    createBtn.textContent = "Creating...";

    var payload = {
      incident_type: document.getElementById("incident_type").value,
      severity: document.getElementById("severity").value,
      description: document.getElementById("description").value,
    };

    fetch("/api/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          setError(createError, result.data.error || "Failed to create incident.");
          return;
        }
        // Refresh the list
        loadIncidents();
        form.reset();
        createSuccess.textContent = "Incident created successfully.";
        show(createSuccess);
        setTimeout(function () { hide(createSuccess); }, 3000);
      })
      .catch(function () {
        setError(createError, "Network error. Is the server running?");
      })
      .finally(function () {
        createBtn.disabled = false;
        createBtn.textContent = "Create Incident";
      });
  });

  // ---------------------------------------------------------------------------
  // Incident listing
  // ---------------------------------------------------------------------------

  function loadIncidents() {
    fetch("/api/incidents")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        renderIncidents(data.incidents || []);
      })
      .catch(function () {
        incidentsList.innerHTML = '<p class="error-message">Failed to load incidents.</p>';
      });
  }

  function renderIncidents(list) {
    incidentCount.textContent = list.length;

    if (list.length === 0) {
      incidentsList.innerHTML = '<p id="no-incidents" class="empty-state">No incidents recorded yet.</p>';
      return;
    }

    var html = list.map(function (inc) {
      var severityClass = "severity-" + (inc.severity || "medium");
      return (
        '<div class="incident-item">' +
          '<div class="incident-info">' +
            '<span class="type">' + escapeHtml(inc.incident_type) + '</span> ' +
            '<span class="severity-badge ' + severityClass + '">' + escapeHtml(inc.severity || "medium") + '</span>' +
            '<p class="desc">' + escapeHtml(inc.description) + '</p>' +
            '<p class="meta">ID: ' + escapeHtml(inc.id) + ' | Created: ' + escapeHtml(inc.created_at) + '</p>' +
          '</div>' +
          '<button class="analyze-btn" data-incident-id="' + escapeHtml(inc.id) + '">Analyze</button>' +
        '</div>'
      );
    }).join("");

    incidentsList.innerHTML = html;

    // Attach analyze handlers to the freshly rendered buttons.
    attachAnalyzeHandlers();
  }

  // ---------------------------------------------------------------------------
  // AI analysis
  // ---------------------------------------------------------------------------

  function requestAnalysis(incidentId, btn) {
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Analyzing...";
    }

    show(analysisSection);
    clearMsg(analysisError);

    // Reset previous analysis display
    aSummary.textContent = "";
    aCause.textContent = "";
    aEvidence.innerHTML = "";
    aRecs.innerHTML = "";
    aSources.textContent = "";

    fetch("/api/incidents/" + incidentId + "/analyze", {
      method: "POST",
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          setError(analysisError, result.data.error || "Analysis failed.");
          return;
        }
        displayAnalysis(result.data);
      })
      .catch(function () {
        setError(analysisError, "Network error. Is the server running?");
      })
      .finally(function () {
        if (btn) {
          btn.disabled = false;
          btn.textContent = "Analyze";
        }
      });
  }

  function displayAnalysis(data) {
    aSummary.textContent = data.summary || "No summary available.";
    aCause.textContent = data.likely_cause || "No likely cause identified.";

    aEvidence.innerHTML = (data.evidence || []).map(function (e) {
      return "<li>" + escapeHtml(e) + "</li>";
    }).join("");

    aRecs.innerHTML = (data.recommendations || []).map(function (r) {
      return "<li>" + escapeHtml(r) + "</li>";
    }).join("");

    aSources.textContent = (data.runbook_sources || []).join(", ") || "No runbooks referenced.";
  }

  // ---------------------------------------------------------------------------
  // Close analysis panel
  // ---------------------------------------------------------------------------

  closeAnalysis.addEventListener("click", function () {
    hide(analysisSection);
  });

  // ---------------------------------------------------------------------------
  // Initialize on page load
  // ---------------------------------------------------------------------------

  // Attach handlers to server-rendered analyze buttons.
  attachAnalyzeHandlers();

  // Refresh incident list from the API (keeps the list in sync after creation).
  loadIncidents();

  function attachAnalyzeHandlers() {
    var buttons = incidentsList.querySelectorAll(".analyze-btn");
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-incident-id");
        requestAnalysis(id, btn);
      });
    });
  }
})();

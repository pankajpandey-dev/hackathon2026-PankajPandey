/* global Chart, fetchJson */
/**
 * Loads /analytics and renders Chart.js visuals on the dashboard.
 * Call destroyDashboardCharts() before re-render; loadDashboardAnalytics() fetches fresh data.
 */
(function () {
  var chartCat = null;
  var chartOut = null;
  var chartConf = null;

  var TICK = "#9aa3b2";
  var GRID = "rgba(42, 48, 64, 0.55)";

  function destroyDashboardCharts() {
    [chartCat, chartOut, chartConf].forEach(function (c) {
      if (c) c.destroy();
    });
    chartCat = chartOut = chartConf = null;
  }

  function barColors(n) {
    var colors = [];
    for (var i = 0; i < n; i++) {
      var h = (i * 47 + 220) % 360;
      colors.push("hsla(" + h + ", 72%, 58%, 0.88)");
    }
    return colors;
  }

  function loadDashboardAnalytics() {
    var errEl = document.getElementById("analytics-err");
    var emptyEl = document.getElementById("analytics-empty");
    if (errEl) errEl.style.display = "none";
    if (emptyEl) emptyEl.style.display = "none";

    return fetchJson("/analytics")
      .then(function (a) {
        destroyDashboardCharts();

        if (typeof Chart === "undefined") {
          throw new Error("Chart.js failed to load.");
        }

        Chart.defaults.font.family = "'DM Sans', system-ui, sans-serif";
        Chart.defaults.color = TICK;

        var cats = a.categories || [];
        var out = a.outcomes || {};
        var bins = a.confidence_bins || [];

        var resolved = out.resolved || 0;
        var escalated = out.escalated || 0;
        var hasAuditData = resolved + escalated > 0 || cats.length > 0;

        if (!hasAuditData && (!bins.length || bins.every(function (b) { return !b.count; }))) {
          if (emptyEl) {
            emptyEl.style.display = "block";
            emptyEl.textContent =
              "No audit data yet. Run all tickets or restore audit_logs/ to see analytics.";
          }
        }

        var elCat = document.getElementById("chart-dash-categories");
        var elOut = document.getElementById("chart-dash-outcomes");
        var elConf = document.getElementById("chart-dash-confidence");

        if (cats.length && elCat) {
          var bg = barColors(cats.length);
          chartCat = new Chart(elCat, {
            type: "bar",
            data: {
              labels: cats.map(function (c) {
                return c.name;
              }),
              datasets: [
                {
                  label: "Tickets",
                  data: cats.map(function (c) {
                    return c.count;
                  }),
                  backgroundColor: bg,
                  borderColor: "rgba(255, 255, 255, 0.12)",
                  borderWidth: 1,
                  borderRadius: 6,
                  borderSkipped: false,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
                title: { display: false },
                tooltip: {
                  backgroundColor: "rgba(15, 17, 23, 0.92)",
                  borderColor: "rgba(99, 102, 241, 0.35)",
                  borderWidth: 1,
                  padding: 10,
                },
              },
              scales: {
                x: {
                  ticks: { color: TICK, maxRotation: 40 },
                  grid: { color: GRID },
                },
                y: {
                  beginAtZero: true,
                  ticks: { color: TICK, stepSize: 1, precision: 0 },
                  grid: { color: GRID },
                },
              },
            },
          });
        }

        if (elOut) {
          var noOutcomes = resolved === 0 && escalated === 0;
          chartOut = new Chart(elOut, {
            type: "doughnut",
            data: noOutcomes
              ? {
                  labels: ["No outcome data yet"],
                  datasets: [
                    {
                      data: [1],
                      backgroundColor: ["rgba(154, 163, 178, 0.35)"],
                      borderColor: ["#0f1117"],
                      borderWidth: 2,
                    },
                  ],
                }
              : {
                  labels: ["Resolved", "Escalated"],
                  datasets: [
                    {
                      data: [resolved, escalated],
                      backgroundColor: [
                        "rgba(52, 211, 153, 0.85)",
                        "rgba(251, 191, 36, 0.88)",
                      ],
                      borderColor: ["#0f1117", "#0f1117"],
                      borderWidth: 3,
                      hoverOffset: 8,
                    },
                  ],
                },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              cutout: "62%",
              plugins: {
                legend: {
                  position: "bottom",
                  labels: {
                    color: TICK,
                    padding: 16,
                    usePointStyle: true,
                  },
                },
                tooltip: {
                  enabled: !noOutcomes,
                  backgroundColor: "rgba(15, 17, 23, 0.92)",
                  borderColor: "rgba(52, 211, 153, 0.25)",
                  borderWidth: 1,
                },
              },
            },
          });
        }

        if (bins.length && elConf) {
          var maxC = Math.max.apply(
            null,
            bins.map(function (b) {
              return b.count;
            })
          );
          var ctxConf = elConf.getContext("2d");
          var gradient = ctxConf.createLinearGradient(0, 0, 0, 260);
          gradient.addColorStop(0, "rgba(167, 139, 250, 0.55)");
          gradient.addColorStop(1, "rgba(99, 102, 241, 0.08)");

          chartConf = new Chart(elConf, {
            type: "bar",
            data: {
              labels: bins.map(function (b) {
                return b.range;
              }),
              datasets: [
                {
                  label: "Think-step count",
                  data: bins.map(function (b) {
                    return b.count;
                  }),
                  backgroundColor: gradient,
                  borderColor: "rgba(167, 139, 250, 0.95)",
                  borderWidth: { top: 2, right: 0, left: 0, bottom: 0 },
                  borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 },
                  barPercentage: 0.92,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
                tooltip: {
                  backgroundColor: "rgba(15, 17, 23, 0.92)",
                  borderColor: "rgba(167, 139, 250, 0.35)",
                  borderWidth: 1,
                },
              },
              scales: {
                x: {
                  title: {
                    display: true,
                    text: "Confidence band (model output)",
                    color: "rgba(154, 163, 178, 0.9)",
                    font: { size: 11 },
                  },
                  ticks: { color: TICK, maxRotation: 45, autoSkip: true },
                  grid: { display: false },
                },
                y: {
                  beginAtZero: true,
                  suggestedMax: maxC < 5 ? 5 : undefined,
                  ticks: { color: TICK, stepSize: 1 },
                  grid: { color: GRID },
                },
              },
            },
          });
        }

        var avgEl = document.getElementById("analytics-avg-confidence");
        var vals = a.confidence_values || [];
        if (avgEl && vals.length) {
          var sum = vals.reduce(function (s, v) {
            return s + v;
          }, 0);
          avgEl.textContent = "Avg confidence (think steps): " + (sum / vals.length).toFixed(2);
          avgEl.style.display = "block";
        } else if (avgEl) {
          avgEl.style.display = "none";
        }
      })
      .catch(function (e) {
        if (errEl) {
          errEl.style.display = "block";
          errEl.textContent = String(e.message || e);
        }
      });
  }

  window.destroyDashboardCharts = destroyDashboardCharts;
  window.loadDashboardAnalytics = loadDashboardAnalytics;
})();

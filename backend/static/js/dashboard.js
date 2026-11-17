// Dashboard charts – all data is injected from the database via json_script.
(function () {
  "use strict";
  var node = document.getElementById("chart-data");
  if (!node || !window.Chart) return;
  var data = JSON.parse(node.textContent);

  Chart.defaults.font.family = '"Segoe UI", system-ui, sans-serif';
  Chart.defaults.color = "#64748b";

  var salesCtx = document.getElementById("salesChart");
  if (salesCtx) {
    new Chart(salesCtx, {
      type: "line",
      data: {
        labels: data.sales_labels,
        datasets: [{
          label: "Sales",
          data: data.sales_values,
          borderColor: "#4f46e5",
          backgroundColor: "rgba(79,70,229,0.12)",
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: "#4f46e5"
        }]
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, grid: { color: "#e2e8f0" } }, x: { grid: { display: false } } }
      }
    });
  }

  var statusCtx = document.getElementById("statusChart");
  if (statusCtx) {
    new Chart(statusCtx, {
      type: "doughnut",
      data: {
        labels: data.status_labels,
        datasets: [{
          data: data.status_values,
          backgroundColor: ["#f59e0b", "#3b82f6", "#22c55e", "#ef4444"],
          borderWidth: 0
        }]
      },
      options: { maintainAspectRatio: false, cutout: "65%", plugins: { legend: { position: "bottom" } } }
    });
  }

  var catCtx = document.getElementById("categoryChart");
  if (catCtx) {
    new Chart(catCtx, {
      type: "bar",
      data: {
        labels: data.category_labels,
        datasets: [{ label: "Units in stock", data: data.category_units, backgroundColor: "#6366f1", borderRadius: 6 }]
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, grid: { color: "#e2e8f0" } }, x: { grid: { display: false } } }
      }
    });
  }
})();

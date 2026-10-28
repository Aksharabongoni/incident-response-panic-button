/**
 * Chart.js Visualizations for Incident Response Panic Button System
 */
const OpsCharts = {
  severityChart: null,
  statusChart: null,
  serviceChart: null,

  init(metrics) {
    if (!metrics) return;
    this.renderSeverityChart(metrics.severity_distribution || {});
    this.renderStatusChart(metrics.status_distribution || {});
    this.renderServiceChart(metrics.service_distribution || {});
  },

  renderSeverityChart(data) {
    const ctx = document.getElementById("severityChart");
    if (!ctx) return;

    if (this.severityChart) {
      this.severityChart.destroy();
    }

    const labels = ["P1 Critical", "P2 High", "P3 Medium", "P4 Low"];
    const values = [
      data["P1_CRITICAL"] || 0,
      data["P2_HIGH"] || 0,
      data["P3_MEDIUM"] || 0,
      data["P4_LOW"] || 0
    ];

    this.severityChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: [
            "#ff3344", // P1
            "#ff9800", // P2
            "#fadb14", // P3
            "#1890ff"  // P4
          ],
          borderColor: "#182238",
          borderWidth: 3,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#f0f6fc", font: { size: 12 } }
          }
        },
        cutout: "68%"
      }
    });
  },

  renderStatusChart(data) {
    const ctx = document.getElementById("statusChart");
    if (!ctx) return;

    if (this.statusChart) {
      this.statusChart.destroy();
    }

    const labels = ["Open", "Acknowledged", "Resolved", "Closed"];
    const values = [
      data["OPEN"] || 0,
      data["ACKNOWLEDGED"] || 0,
      data["RESOLVED"] || 0,
      data["CLOSED"] || 0
    ];

    this.statusChart = new Chart(ctx, {
      type: "pie",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: [
            "#ff4d5e", // Open
            "#ffab00", // Acknowledged
            "#00e676", // Resolved
            "#8c8c8c"  // Closed
          ],
          borderColor: "#182238",
          borderWidth: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#f0f6fc", font: { size: 12 } }
          }
        }
      }
    });
  },

  renderServiceChart(data) {
    const ctx = document.getElementById("serviceChart");
    if (!ctx) return;

    if (this.serviceChart) {
      this.serviceChart.destroy();
    }

    const labels = Object.keys(data);
    const values = Object.values(data);

    this.serviceChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels.length ? labels : ["No data"],
        datasets: [{
          label: "Incident Count",
          data: values.length ? values : [0],
          backgroundColor: "rgba(0, 229, 255, 0.4)",
          borderColor: "#00e5ff",
          borderWidth: 1.5,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        scales: {
          x: {
            grid: { color: "#263554" },
            ticks: { color: "#8b949e", precision: 0 }
          },
          y: {
            grid: { color: "transparent" },
            ticks: { color: "#f0f6fc" }
          }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  }
};

window.OpsCharts = OpsCharts;


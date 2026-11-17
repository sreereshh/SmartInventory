// Smart Inventory – shared UI behaviour
(function () {
  "use strict";

  // Mobile sidebar toggle
  var sidebar = document.getElementById("sidebar");
  var backdrop = document.getElementById("sidebarBackdrop");
  var toggle = document.getElementById("sidebarToggle");
  function setSidebar(open) {
    if (!sidebar) return;
    sidebar.classList.toggle("show", open);
    if (backdrop) backdrop.classList.toggle("show", open);
  }
  if (toggle) toggle.addEventListener("click", function () { setSidebar(!sidebar.classList.contains("show")); });
  if (backdrop) backdrop.addEventListener("click", function () { setSidebar(false); });

  // Auto-dismiss success/info alerts after a few seconds (warnings & errors stay)
  document.querySelectorAll(".alert[data-autohide='true']").forEach(function (el) {
    setTimeout(function () {
      if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(el).close();
    }, 6000);
  });

  // Filters: submit the form automatically when a <select data-autosubmit> changes
  document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
    select.addEventListener("change", function () { select.form.submit(); });
  });

  // Prevent double submits
  document.querySelectorAll("form[data-once]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var btn = form.querySelector("button[type=submit]");
      if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving…'; }
    });
  });

  // Print buttons
  document.querySelectorAll("[data-print]").forEach(function (btn) {
    btn.addEventListener("click", function () { window.print(); });
  });
})();

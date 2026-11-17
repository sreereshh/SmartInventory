// Dynamic order form: add/remove product lines, live line totals and grand total.
// The server re-validates everything (stock, quantities) when the order is saved.
(function () {
  "use strict";

  var products = JSON.parse(document.getElementById("product-data").textContent);
  var initialRows = JSON.parse(document.getElementById("initial-rows").textContent);
  var currency = window.ORDER_CURRENCY || "";
  var byId = {};
  products.forEach(function (p) { byId[String(p.id)] = p; });

  var linesEl = document.getElementById("orderLines");
  var addBtn = document.getElementById("addLine");
  var form = document.getElementById("orderForm");

  function money(n) {
    return currency + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function optionsHtml(selectedId) {
    var html = '<option value="">— Select product —</option>';
    products.forEach(function (p) {
      var disabled = p.stock <= 0 ? " disabled" : "";
      var sel = String(selectedId) === String(p.id) ? " selected" : "";
      var label = p.name + " (" + p.code + ") – " + (p.stock > 0 ? p.stock + " in stock" : "out of stock") + " – " + money(p.price);
      html += '<option value="' + p.id + '"' + sel + disabled + ">" + label.replace(/</g, "&lt;") + "</option>";
    });
    return html;
  }

  function addLine(productId, quantity) {
    var row = document.createElement("div");
    row.className = "line-row";
    row.innerHTML =
      '<div class="row g-2 align-items-center">' +
        '<div class="col-md-6"><select name="product" class="form-select line-product" required>' + optionsHtml(productId) + "</select></div>" +
        '<div class="col-4 col-md-2"><input type="number" name="quantity" class="form-control line-qty" min="1" step="1" value="' + (quantity || 1) + '" required></div>' +
        '<div class="col-6 col-md-3 text-md-end"><div class="small text-muted line-meta">&nbsp;</div><div class="fw-semibold line-total">' + money(0) + "</div></div>" +
        '<div class="col-2 col-md-1 text-end"><button type="button" class="btn btn-sm btn-outline-danger remove-line" title="Remove"><i class="bi bi-trash"></i></button></div>' +
      "</div>" +
      '<div class="text-danger small mt-1 line-error" style="display:none"></div>';
    linesEl.appendChild(row);
    refreshLine(row);
    recalc();
  }

  function refreshLine(row) {
    var select = row.querySelector(".line-product");
    var qtyInput = row.querySelector(".line-qty");
    var meta = row.querySelector(".line-meta");
    var total = row.querySelector(".line-total");
    var err = row.querySelector(".line-error");
    var product = byId[select.value];
    var qty = parseInt(qtyInput.value, 10);
    err.style.display = "none";
    if (!product) { meta.innerHTML = "&nbsp;"; total.textContent = money(0); return 0; }
    qtyInput.max = product.stock;
    meta.textContent = money(product.price) + " each";
    if (isNaN(qty) || qty < 1) { total.textContent = money(0); return 0; }
    if (qty > product.stock) {
      err.textContent = "Only " + product.stock + " unit(s) available for " + product.name + ".";
      err.style.display = "block";
    }
    var lineTotal = product.price * qty;
    total.textContent = money(lineTotal);
    return lineTotal;
  }

  function recalc() {
    var rows = linesEl.querySelectorAll(".line-row");
    var sum = 0, units = 0, lines = 0;
    rows.forEach(function (row) {
      var product = byId[row.querySelector(".line-product").value];
      var qty = parseInt(row.querySelector(".line-qty").value, 10);
      sum += refreshLine(row);
      if (product && qty > 0) { lines += 1; units += qty; }
    });
    document.getElementById("sumLines").textContent = lines;
    document.getElementById("sumUnits").textContent = units;
    document.getElementById("sumSubtotal").textContent = money(sum);
    document.getElementById("grandTotal").textContent = money(sum);
  }

  linesEl.addEventListener("input", recalc);
  linesEl.addEventListener("change", recalc);
  linesEl.addEventListener("click", function (e) {
    var btn = e.target.closest(".remove-line");
    if (!btn) return;
    btn.closest(".line-row").remove();
    if (!linesEl.children.length) addLine();
    recalc();
  });
  addBtn.addEventListener("click", function () { addLine(); });

  form.addEventListener("submit", function (e) {
    var customer = document.getElementById("customer");
    var valid = true;
    if (!customer.value) { customer.classList.add("is-invalid"); valid = false; } else { customer.classList.remove("is-invalid"); }
    var filled = 0;
    linesEl.querySelectorAll(".line-row").forEach(function (row) {
      var product = byId[row.querySelector(".line-product").value];
      var qty = parseInt(row.querySelector(".line-qty").value, 10);
      if (product) {
        filled += 1;
        if (isNaN(qty) || qty < 1 || qty > product.stock) valid = false;
      }
    });
    if (!filled) { alert("Add at least one product."); valid = false; }
    if (!valid) { e.preventDefault(); return; }
    var btn = document.getElementById("submitOrder");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving…';
  });

  if (initialRows.length) {
    initialRows.forEach(function (r) { addLine(r.product, r.quantity); });
  } else {
    addLine();
  }
})();

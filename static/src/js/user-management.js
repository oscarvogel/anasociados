(function () {
  const clientSelect = document.getElementById("id_cliente");
  const assignmentList = document.querySelector("[data-area-list]");
  const addAreaButton = document.querySelector("[data-add-area]");
  const template = document.getElementById("empty-area-assignment-template");
  const totalForms = document.getElementById("id_areas-TOTAL_FORMS");
  const optionsScript = document.getElementById("client-area-options");

  if (!clientSelect || !assignmentList || !addAreaButton || !template || !totalForms || !optionsScript) return;

  let clientAreas = {};
  try {
    clientAreas = JSON.parse(optionsScript.textContent || "{}");
  } catch (_error) {
    clientAreas = {};
  }

  function updateAreaSelect(select, preserveCurrent = true) {
    const currentValue = preserveCurrent ? select.value : "";
    const placeholder = select.dataset.placeholder || "Seleccioná un área";
    const options = clientAreas[clientSelect.value] || [];

    select.replaceChildren(new Option(placeholder, ""));
    options.forEach((area) => select.add(new Option(area.label, area.id)));

    if (preserveCurrent && options.some((area) => String(area.id) === currentValue)) {
      select.value = currentValue;
    }
  }

  function updateAllAreaSelects(preserveCurrent = true) {
    assignmentList.querySelectorAll('select[name$="-area"]').forEach((select) => {
      updateAreaSelect(select, preserveCurrent);
    });
  }

  function syncDeletedRows() {
    assignmentList.querySelectorAll('[name$="-DELETE"]').forEach((checkbox) => {
      const row = checkbox.closest("[data-area-row]");
      if (row) row.hidden = checkbox.checked;
    });
  }

  assignmentList.querySelectorAll('select[name$="-area"]').forEach((select) => {
    if (select.options.length) select.dataset.placeholder = select.options[0].textContent;
  });
  updateAllAreaSelects(true);
  syncDeletedRows();

  clientSelect.addEventListener("change", () => updateAllAreaSelects(false));

  addAreaButton.addEventListener("click", () => {
    const index = Number.parseInt(totalForms.value, 10);
    const html = template.innerHTML.replaceAll("__prefix__", String(index));
    const holder = document.createElement("div");
    holder.innerHTML = html.trim();
    const row = holder.firstElementChild;
    if (!row) return;

    assignmentList.appendChild(row);
    totalForms.value = String(index + 1);
    const select = row.querySelector('select[name$="-area"]');
    if (select) {
      select.dataset.placeholder = select.options.length ? select.options[0].textContent : "Seleccioná un área";
      updateAreaSelect(select, false);
      select.focus();
    }
  });

  assignmentList.addEventListener("change", (event) => {
    if (!event.target.matches('[name$="-DELETE"]')) return;
    const row = event.target.closest("[data-area-row]");
    if (row) row.hidden = event.target.checked;
  });
})();

(function () {
  const input = document.querySelector("[data-menu-search]");
  const menu = document.querySelector("[data-menu-list]");
  const emptyState = document.querySelector("[data-menu-empty]");

  if (!input || !menu) return;

  const normalize = (value) =>
    (value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase();

  const groups = Array.from(menu.querySelectorAll("[data-menu-group]"));

  function filterMenu() {
    const query = normalize(input.value.trim());
    let visibleItems = 0;

    groups.forEach((group) => {
      const groupLabel = normalize(group.dataset.menuGroupLabel);
      const groupMatches = Boolean(query) && groupLabel.includes(query);
      const items = Array.from(group.querySelectorAll("[data-menu-item]"));
      let visibleInGroup = 0;

      items.forEach((item) => {
        const itemMatches = !query || groupMatches || normalize(item.dataset.menuSearchText).includes(query);
        item.hidden = !itemMatches;
        if (itemMatches) visibleInGroup += 1;
      });

      const groupIsVisible = visibleInGroup > 0;
      group.hidden = !groupIsVisible;
      visibleItems += visibleInGroup;

      if (!group.dataset.menuStandalone && query && groupIsVisible) {
        const trigger = group.querySelector(":scope > a.nav-link");
        if (trigger && !group.classList.contains("pcoded-trigger")) {
          group.dataset.menuSearchExpanded = "true";
          group.classList.add("pcoded-trigger");
          trigger.setAttribute("aria-expanded", "true");
        }
      }

      if (!query && group.dataset.menuSearchExpanded === "true") {
        group.classList.remove("pcoded-trigger");
        const trigger = group.querySelector(":scope > a.nav-link");
        if (trigger) trigger.setAttribute("aria-expanded", "false");
        delete group.dataset.menuSearchExpanded;
      }
    });

    if (emptyState) emptyState.hidden = !query || visibleItems > 0;
  }

  input.addEventListener("input", filterMenu);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && input.value) {
      input.value = "";
      filterMenu();
    }
  });
})();

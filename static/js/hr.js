let currentLocationId = null;
let allOwners = {};
let currentDay = null;
let selectedDirectorUserId = null;

document.addEventListener("DOMContentLoaded", async () => {
  const dateInput = document.getElementById("dateFilter");
  const today = new Date().toISOString().slice(0, 10);
  dateInput.value = today;
  currentDay = today;

  await loadDirectors();
  // when directorSelect changes, switch currentLocationId to that director's location
  const directorSelectEl = document.getElementById("directorSelect");
  if (directorSelectEl) {
    directorSelectEl.addEventListener("change", () => {
      const sel = directorSelectEl;
      selectedDirectorUserId = sel.value || null;
      const chosen = sel.options[sel.selectedIndex];
      const locId = chosen && chosen.dataset ? chosen.dataset.locationId : null;
      if (locId) {
        currentLocationId = locId;
      }
      loadAll();
    });
  }
  await loadLocations();
  loadAllOwners();

  const createLocationBtn = document.getElementById("createLocationBtn");
  if (createLocationBtn)
    createLocationBtn.addEventListener("click", createLocation);
  const ownerCreateBtn = document.getElementById("ownerCreateBtn");
  if (ownerCreateBtn) ownerCreateBtn.addEventListener("click", createOwner);
  const ownerSearch = document.getElementById("ownerSearch");
  if (ownerSearch)
    ownerSearch.addEventListener("input", () => {
      ownersManagePage = 1;
      ownersManageSearch = ownerSearch.value.trim();
      loadOwnersManage(1);
    });
  const ownersPrev = document.getElementById("ownersPrev");
  const ownersNext = document.getElementById("ownersNext");
  if (ownersPrev)
    ownersPrev.addEventListener("click", () =>
      loadOwnersManage(Math.max(1, ownersManagePage - 1)),
    );
  if (ownersNext)
    ownersNext.addEventListener("click", () =>
      loadOwnersManage(ownersManagePage + 1),
    );

  // load assignments when chosen location changes
  const assignLocationSelectEl = document.getElementById(
    "assignLocationSelect",
  );
  if (assignLocationSelectEl)
    assignLocationSelectEl.addEventListener("change", () => {
      currentLocationId = assignLocationSelectEl.value;
      loadOwnerAssignments();
      loadAll();
    });
  const assignSaveBtn = document.getElementById("assignSaveBtn");
  if (assignSaveBtn)
    assignSaveBtn.addEventListener("click", saveOwnerAssignments);
  const assignClearBtn = document.getElementById("assignClearBtn");
  if (assignClearBtn)
    assignClearBtn.addEventListener("click", clearOwnerAssignments);

  // Add event listener for save stats button
  const saveStatsBtn = document.getElementById("saveStats");
  if (saveStatsBtn) saveStatsBtn.addEventListener("click", saveStats);

  const dateFilterEl = document.getElementById("dateFilter");
  if (dateFilterEl)
    dateFilterEl.addEventListener("change", () => {
      currentDay = dateFilterEl.value;
      updateEditableStatus();
      loadDirectors(currentDay); // Reload directors for the selected date
      loadAll();
    });
  // Load admin data when page loads (only sections that exist in DOM)
  loadAdminData();
  // Load owners management first page if UI exists
  ownersManagePage = 1;
  ownersManagePageSize = 10;
  ownersManageSearch = "";
  if (document.getElementById("ownersManageList")) {
    loadOwnersManage(1);
  }
  // initial load for current date
  loadAll();

  // Load director warehouses management UI
  loadDirectorWarehousesManagement();
});

// Owners management state
let ownersManagePage = 1;
let ownersManagePageSize = 10;
let ownersManageSearch = "";

async function loadAdminData() {
  if (document.getElementById("adminEmployeesList")) {
    await loadAdminEmployees();
  }
  if (document.getElementById("adminDirectorsList")) {
    await loadAdminDirectors();
  }
  if (document.getElementById("adminLocationsList")) {
    await loadAdminLocations();
  }
}

/* Admin: Employees */
async function loadAdminEmployees() {
  try {
    const res = await fetch("/hr_admin/employees", { credentials: "include" });
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById("adminEmployeesList");
    if (!list) return;
    list.innerHTML = "";
    data.employees.forEach((e) => {
      const el = document.createElement("div");
      el.className =
        "list-group-item d-flex justify-content-between align-items-center";
      el.innerHTML = `
        <div>
          <strong>${e.name}</strong> <small class="text-muted">#${e.id}</small>
        </div>
        <div>
          <button class="btn btn-sm btn-secondary me-1" onclick="editEmployeePrompt(${
            e.id
          }, '${escapeHtml(e.name)}')">Изменить</button>
          <button class="btn btn-sm btn-danger" onclick="fireEmployee(${
            e.id
          })">Уволить</button>
        </div>
      `;
      list.appendChild(el);
    });
  } catch (e) {
    console.error("loadAdminEmployees", e);
  }
}

/* Owners management (CRUD + pagination + search) */
async function loadOwnersManage(page = 1) {
  ownersManagePage = page;
  try {
    const res = await fetch("/owners", { credentials: "include" });
    if (!res.ok) return;
    const data = await res.json();
    // data is array of owners
    const arr = data.filter(
      (o) =>
        !ownersManageSearch ||
        o.name.toLowerCase().includes(ownersManageSearch.toLowerCase()),
    );
    const total = arr.length;
    const start = (ownersManagePage - 1) * ownersManagePageSize;
    const pageItems = arr.slice(start, start + ownersManagePageSize);
    const list = document.getElementById("ownersManageList");
    list.innerHTML = "";
    pageItems.forEach((o) => {
      const el = document.createElement("div");
      el.className =
        "list-group-item d-flex justify-content-between align-items-center";
      el.innerHTML = `<div><strong>${
        o.name
      }</strong> <small class="text-muted">#${
        o.id
      }</small></div><div><button class="btn btn-sm btn-secondary me-1" onclick="editOwnerPrompt(${
        o.id
      }, '${escapeHtml(
        o.name,
      )}')">Изменить</button><button class="btn btn-sm btn-danger" onclick="deleteOwner(${
        o.id
      })">Удалить</button></div>`;
      list.appendChild(el);
    });
    const pageEl = document.getElementById("ownersPage");
    if (pageEl) pageEl.textContent = String(ownersManagePage);
    // update prev/next disable
    const prev = document.getElementById("ownersPrev");
    const next = document.getElementById("ownersNext");
    if (prev) prev.disabled = ownersManagePage <= 1;
    if (next) next.disabled = start + ownersManagePageSize >= total;
    // Also refresh allOwners cache
    allOwners = {};
    data.forEach((o) => (allOwners[o.id] = o.name));
    // populate available list for assignments if exists
    const avail = document.getElementById("assignAvailableList");
    if (avail) {
      avail.innerHTML = "";
      Object.entries(allOwners).forEach(([id, name]) => {
        const item = document.createElement("div");
        item.className =
          "list-group-item d-flex justify-content-between align-items-center";
        item.setAttribute("data-owner-id", id);
        item.innerHTML = `<div>${escapeHtml(
          name,
        )} <small class="text-muted">#${id}</small></div><div><button class="btn btn-sm btn-primary" onclick="assignOwnerAdd(${id})">Добавить</button></div>`;
        avail.appendChild(item);
      });
    }
  } catch (e) {
    console.error("loadOwnersManage", e);
  }
}

async function createOwner() {
  const name = await showPromptModal("Создать owner", "Введите имя owner", "");
  if (!name) return;
  try {
    const body = JSON.stringify({ name });
    const res = await fetch("/owners", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body,
    });
    if (res.ok) {
      loadOwnersManage(1);
      loadAllOwners();
      showToast("Owner создан", "success");
    } else {
      showToast("Ошибка при создании owner", "error");
    }
  } catch (e) {
    console.error(e);
  }
}

async function editOwnerPrompt(id, currentName) {
  const nv = await showPromptModal(
    "Редактировать owner",
    "Новое имя",
    currentName,
  );
  if (nv !== null) editOwner(id, nv);
}

async function editOwner(id, name) {
  try {
    const res = await fetch(`/owners/${id}`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (res.ok) {
      loadOwnersManage(ownersManagePage);
      loadAllOwners();
    } else showToast("Ошибка при обновлении", "error");
  } catch (e) {
    console.error(e);
  }
}

async function deleteOwner(id) {
  const ok = await showConfirmModal("Удалить owner?");
  if (!ok) return;
  try {
    const res = await fetch(`/owners/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (res.ok) {
      loadOwnersManage(ownersManagePage);
      loadAllOwners();
    } else showToast("Ошибка при удалении", "error");
  } catch (e) {
    console.error(e);
  }
}

/* Owner assignments */
async function loadOwnerAssignments() {
  const locEl = document.getElementById("assignLocationSelect");
  const loc = locEl ? locEl.value : currentLocationId;
  const day = currentDay || new Date().toISOString().slice(0, 10);
  if (!loc) {
    // Silently return instead of showing error - location might not be selected yet
    console.log("Location not selected, skipping loadOwnerAssignments");
    return;
  }
  try {
    const res = await fetch(`/locations/${loc}/assignments?day=${day}`, {
      credentials: "include",
    });
    if (!res.ok) return showToast("Не удалось загрузить привязки", "error");
    const d = await res.json();
    const assignedIds = d.owners.map((o) => String(o.id));
    const cur = document.getElementById("assignCurrentList");
    const avail = document.getElementById("assignAvailableList");
    if (cur) cur.innerHTML = "";
    if (avail) avail.innerHTML = "";

    // populate assigned list
    d.owners.forEach((o) => {
      if (!cur) return;
      const li = document.createElement("div");
      li.className =
        "list-group-item d-flex justify-content-between align-items-center";
      li.setAttribute("data-owner-id", String(o.id));
      li.innerHTML = `<div>${escapeHtml(o.name)} <small class="text-muted">#${
        o.id
      }</small></div><div><button class="btn btn-sm btn-outline-danger" onclick="removeAssignedOwner(${
        o.id
      })">Удалить</button></div>`;
      cur.appendChild(li);
    });

    // populate available list with owners not assigned
    Object.entries(allOwners).forEach(([id, name]) => {
      if (assignedIds.includes(id)) return;
      if (!avail) return;
      const item = document.createElement("div");
      item.className =
        "list-group-item d-flex justify-content-between align-items-center";
      item.setAttribute("data-owner-id", id);
      item.innerHTML = `<div>${escapeHtml(
        name,
      )} <small class="text-muted">#${id}</small></div><div><button class="btn btn-sm btn-primary" onclick="assignOwnerAdd(${id})">Добавить</button></div>`;
      avail.appendChild(item);
    });
  } catch (e) {
    console.error(e);
  }
}

async function saveOwnerAssignments() {
  const locEl = document.getElementById("assignLocationSelect");
  const loc = locEl ? locEl.value : currentLocationId;
  const day = currentDay || new Date().toISOString().slice(0, 10);
  if (!loc) {
    showToast("Выберите локацию", "error");
    return;
  }
  const cur = document.getElementById("assignCurrentList");
  const selectedIds = [];
  if (cur) {
    Array.from(cur.children).forEach((c) => {
      const id = c.getAttribute("data-owner-id");
      if (id) selectedIds.push(parseInt(id));
    });
  }

  console.log("Saving owner assignments:", {
    locationId: loc,
    day: day,
    ownerIds: selectedIds,
  });

  try {
    const res = await fetch(`/locations/${loc}/assignments?day=${day}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(selectedIds),
    });
    if (res.ok) {
      showToast("Привязки сохранены", "success");
      console.log("Owner assignments saved successfully");
      loadOwnerAssignments();
      loadAllOwners();
    } else {
      const txt = await res.text();
      console.error("Failed to save assignments:", txt);
      showToast("Ошибка: " + txt, "error");
    }
  } catch (e) {
    console.error(e);
  }
}

async function clearOwnerAssignments() {
  const ok = await showConfirmModal(
    "Снять всех владельцев с склада на выбранную дату?",
  );
  if (!ok) return;
  const locEl = document.getElementById("assignLocationSelect");
  const loc = locEl ? locEl.value : currentLocationId;
  const day = currentDay || new Date().toISOString().slice(0, 10);

  if (!loc) {
    showToast("Выберите локацию", "error");
    return;
  }

  console.log("Clearing owner assignments for location:", loc, "day:", day);

  try {
    const res = await fetch(`/locations/${loc}/assignments?day=${day}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify([]),
    });
    if (res.ok) {
      showToast("Привязки очищены", "success");
      console.log("Owner assignments cleared successfully");
      loadOwnerAssignments();
      loadAllOwners();
    } else {
      console.error("Failed to clear assignments, status:", res.status);
      showToast("Ошибка при очистке", "error");
    }
  } catch (e) {
    console.error("Error clearing assignments:", e);
    showToast("Ошибка при очистке", "error");
  }
}

// Add / Remove helpers for the new available/assigned UI
function assignOwnerAdd(id) {
  const idStr = String(id);
  const cur = document.getElementById("assignCurrentList");
  if (!cur) return;
  if (cur.querySelector(`[data-owner-id='${idStr}']`)) return;
  const name = allOwners[id];
  const el = document.createElement("div");
  el.className =
    "list-group-item d-flex justify-content-between align-items-center";
  el.setAttribute("data-owner-id", idStr);
  el.innerHTML = `<div>${escapeHtml(
    name,
  )} <small class="text-muted">#${idStr}</small></div><div><button class="btn btn-sm btn-outline-danger" onclick="removeAssignedOwner(${id})">Удалить</button></div>`;
  cur.appendChild(el);
  // remove from available
  const avail = document.getElementById("assignAvailableList");
  const a = avail && avail.querySelector(`[data-owner-id='${idStr}']`);
  if (a) a.remove();
}

function removeAssignedOwner(id) {
  const idStr = String(id);
  const cur = document.getElementById("assignCurrentList");
  const el = cur && cur.querySelector(`[data-owner-id='${idStr}']`);
  if (el) el.remove();
  // re-add to available
  const avail = document.getElementById("assignAvailableList");
  if (avail) {
    const name = allOwners[id];
    const d = document.createElement("div");
    d.className =
      "list-group-item d-flex justify-content-between align-items-center";
    d.setAttribute("data-owner-id", idStr);
    d.innerHTML = `<div>${escapeHtml(
      name,
    )} <small class="text-muted">#${idStr}</small></div><div><button class="btn btn-sm btn-primary" onclick="assignOwnerAdd(${id})">Добавить</button></div>`;
    avail.appendChild(d);
  }
}

function escapeHtml(s) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };
  return String(s).replace(/[&<>"']/g, (c) => map[c]);
}

// Modal helpers (return Promises)
function showPromptModal(title, placeholder = "", defaultValue = "") {
  return new Promise((resolve) => {
    const modalEl = document.getElementById("genericModal");
    const modal = new bootstrap.Modal(modalEl);
    document.getElementById("genericModalTitle").textContent = title;
    document.getElementById("genericModalBody").textContent = placeholder;
    const input = document.getElementById("genericModalInput");
    input.value = defaultValue || "";
    input.focus();

    function onConfirm() {
      cleanup();
      resolve(input.value);
    }
    function onCancel() {
      cleanup();
      resolve(null);
    }
    function cleanup() {
      document
        .getElementById("genericModalConfirm")
        .removeEventListener("click", onConfirm);
      document
        .getElementById("genericModalCancel")
        .removeEventListener("click", onCancel);
      modal.hide();
    }

    document
      .getElementById("genericModalConfirm")
      .addEventListener("click", onConfirm);
    document
      .getElementById("genericModalCancel")
      .addEventListener("click", onCancel);
    modal.show();
  });
}

function showConfirmModal(message) {
  return new Promise((resolve) => {
    const modalEl = document.getElementById("confirmModal");
    const modal = new bootstrap.Modal(modalEl);
    document.getElementById("confirmModalBody").textContent = message;

    function onConfirm() {
      cleanup();
      resolve(true);
    }
    function onCancel() {
      cleanup();
      resolve(false);
    }
    function cleanup() {
      document
        .getElementById("confirmModalConfirm")
        .removeEventListener("click", onConfirm);
      document
        .getElementById("confirmModalCancel")
        .removeEventListener("click", onCancel);
      modal.hide();
    }

    document
      .getElementById("confirmModalConfirm")
      .addEventListener("click", onConfirm);
    document
      .getElementById("confirmModalCancel")
      .addEventListener("click", onCancel);
    modal.show();
  });
}

async function createEmployee() {
  const nameEl = document.getElementById("newEmployeeName");
  if (!nameEl) {
    showToast("Элемент не найден", "error");
    return;
  }
  const name = nameEl.value.trim();
  if (!name) {
    showToast("Введите имя", "error");
    return;
  }
  try {
    const res = await fetch(
      `/hr_admin/employees?name=${encodeURIComponent(name)}`,
      { method: "POST", credentials: "include" },
    );
    if (res.ok) {
      const nameEl = document.getElementById("newEmployeeName");
      if (nameEl) nameEl.value = "";
      loadAdminEmployees();
      loadAll();
    } else showToast("Ошибка при создании", "error");
  } catch (e) {
    console.error(e);
  }
}

async function editEmployeePrompt(id, currentName) {
  const nv = await showPromptModal(
    "Редактировать сотрудника",
    "Новое имя сотрудника",
    currentName,
  );
  if (nv !== null) {
    editEmployee(id, nv);
  }
}

async function editEmployee(id, name) {
  try {
    const res = await fetch(
      `/hr_admin/employees/${id}?name=${encodeURIComponent(name)}`,
      { method: "PUT", credentials: "include" },
    );
    if (res.ok) {
      loadAdminEmployees();
      loadAll();
    } else showToast("Ошибка при обновлении", "error");
  } catch (e) {
    console.error(e);
  }
}

async function fireEmployee(id) {
  const ok = await showConfirmModal("Уволить сотрудника?");
  if (!ok) return;
  try {
    const res = await fetch(`/hr_admin/employees/${id}/fire`, {
      method: "POST",
      credentials: "include",
    });
    if (res.ok) {
      loadAdminEmployees();
      loadAll();
    } else showToast("Ошибка при увольнении", "error");
  } catch (e) {
    console.error(e);
  }
}

/* Admin: Directors */
async function loadAdminDirectors() {
  try {
    const [res, locsRes] = await Promise.all([
      fetch("/hr_admin/directors", { credentials: "include" }),
      fetch("/hr_admin/locations", { credentials: "include" }),
    ]);
    if (!res.ok) return;
    const data = await res.json();
    const locs = locsRes.ok ? await locsRes.json() : { locations: [] };

    const locMap = {};
    (locs.locations || []).forEach((l) => (locMap[l.id] = l.location_name));

    const list = document.getElementById("adminDirectorsList");
    if (!list) return;
    list.innerHTML = "";
    data.directors.forEach((d) => {
      const el = document.createElement("div");
      el.className =
        "list-group-item d-flex justify-content-between align-items-center";
      const userLabel =
        d.name || d.user_name || d.user_email || `Пользователь #${d.user_id}`;
      const locLabel = locMap[d.location_id] || `Локация #${d.location_id}`;
      const statusBadge =
        d.is_active === false
          ? '<span class="badge bg-danger ms-2">Неактивен</span>'
          : "";
      el.innerHTML = `
          <div><strong>${escapeHtml(
            userLabel,
          )}</strong> ${statusBadge} — ${escapeHtml(locLabel)}</div>
          <div>
            <button class="btn btn-sm btn-secondary me-1" onclick="editDirectorPrompt(${
              d.user_id
            }, ${d.location_id})">Изменить</button>
            <button class="btn btn-sm btn-danger" onclick="deleteDirector(${
              d.user_id
            })">Удалить</button>
          </div>
        `;
      list.appendChild(el);
    });

    // fill location select for create (if UI exists)
    const locSel = document.getElementById("newDirectorLocation");
    if (locSel) {
      locSel.innerHTML = "";
      (locs.locations || []).forEach((l) => {
        const o = document.createElement("option");
        o.value = l.id;
        o.textContent = l.location_name;
        locSel.appendChild(o);
      });
    }
  } catch (e) {
    console.error(e);
  }
}

async function createDirector() {
  const userIdEl = document.getElementById("newDirectorUserId");
  const locEl = document.getElementById("newDirectorLocation");
  if (!userIdEl || !locEl) {
    showToast("Элементы не найдены", "error");
    return;
  }
  const userId = userIdEl.value.trim();
  const loc = locEl.value;
  if (!userId || !loc) {
    showToast("Введите user_id и выберите локацию", "error");
    return;
  }
  try {
    const res = await fetch(
      `/hr_admin/directors?user_id=${encodeURIComponent(
        userId,
      )}&location_id=${encodeURIComponent(loc)}`,
      { method: "POST", credentials: "include" },
    );
    if (res.ok) {
      const userIdEl = document.getElementById("newDirectorUserId");
      if (userIdEl) userIdEl.value = "";
      loadAdminDirectors();
      loadDirectors();
    } else showToast("Ошибка при создании директора", "error");
  } catch (e) {
    console.error(e);
  }
}

async function editDirectorPrompt(userId, currentLoc) {
  // build location options from existing select if present, otherwise fetch
  const locSel = document.getElementById("newDirectorLocation");
  let options = [];
  if (locSel && locSel.options.length) {
    Array.from(locSel.options).forEach((o) =>
      options.push({ value: o.value, text: o.textContent }),
    );
  } else {
    try {
      const r = await fetch("/hr_admin/locations", { credentials: "include" });
      if (r.ok) {
        const data = await r.json();
        (data.locations || []).forEach((l) =>
          options.push({ value: l.id, text: l.location_name }),
        );
      }
    } catch (e) {
      console.error(e);
    }
  }
  const nv = await showSelectModal(
    "Выберите локацию для директора",
    options,
    String(currentLoc),
  );
  if (nv !== null) editDirector(userId, nv);
}

async function editDirector(userId, locationId) {
  try {
    const res = await fetch(
      `/hr_admin/directors/${userId}?location_id=${encodeURIComponent(
        locationId,
      )}`,
      { method: "PUT", credentials: "include" },
    );
    if (res.ok) {
      loadAdminDirectors();
      loadDirectors();
    } else showToast("Ошибка при обновлении", "error");
  } catch (e) {
    console.error(e);
  }
}

async function deleteDirector(userId) {
  const ok = await showConfirmModal("Удалить директора?");
  if (!ok) return;
  try {
    const res = await fetch(`/hr_admin/directors/${userId}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (res.ok) {
      loadAdminDirectors();
      loadDirectors();
    } else showToast("Ошибка при удалении", "error");
  } catch (e) {
    console.error(e);
  }
}

/* Admin: Locations */
async function loadAdminLocations() {
  try {
    const res = await fetch("/hr_admin/locations", { credentials: "include" });
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById("adminLocationsList");
    if (!list) return;
    list.innerHTML = "";
    data.locations.forEach((l) => {
      const el = document.createElement("div");
      el.className =
        "list-group-item d-flex justify-content-between align-items-center";
      el.innerHTML = `
        <div>${l.location_name} <small class="text-muted">#${l.id}</small></div>
        <div>
          <button class="btn btn-sm btn-secondary me-1" onclick="editLocationPrompt(${
            l.id
          }, '${escapeHtml(l.location_name)}')">Изменить</button>
          <button class="btn btn-sm btn-danger" onclick="deleteLocation(${
            l.id
          })">Удалить</button>
        </div>
      `;
      list.appendChild(el);
    });
  } catch (e) {
    console.error(e);
  }
}

async function createLocation() {
  const nameEl = document.getElementById("newLocationName");
  if (!nameEl) {
    showToast("Элемент не найден", "error");
    return;
  }
  const name = nameEl.value.trim();
  if (!name) {
    showToast("Введите название склада", "error");
    return;
  }
  try {
    const res = await fetch(
      `/hr_admin/locations?location_name=${encodeURIComponent(name)}`,
      { method: "POST", credentials: "include" },
    );
    if (res.ok) {
      const nameEl = document.getElementById("newLocationName");
      if (nameEl) nameEl.value = "";
      loadAdminLocations();
      loadLocations();
    } else showToast("Ошибка при создании", "error");
  } catch (e) {
    console.error(e);
  }
}

function editLocationPrompt(id, currentName) {
  showPromptModal(
    "Редактировать склад",
    "Новое название склада",
    currentName,
  ).then((nv) => {
    if (nv !== null) editLocation(id, nv);
  });
}

async function editLocation(id, name) {
  try {
    const res = await fetch(
      `/hr_admin/locations/${id}?location_name=${encodeURIComponent(name)}`,
      { method: "PUT", credentials: "include" },
    );
    if (res.ok) {
      loadAdminLocations();
      loadLocations();
    } else showToast("Ошибка при обновлении", "error");
  } catch (e) {
    console.error(e);
  }
}

async function deleteLocation(id) {
  const ok = await showConfirmModal("Удалить локацию?");
  if (!ok) return;
  try {
    const res = await fetch(`/hr_admin/locations/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (res.ok) {
      loadAdminLocations();
      loadLocations();
    } else showToast("Ошибка при удалении", "error");
  } catch (e) {
    console.error(e);
  }
}

async function loadDirectors(day = null) {
  try {
    const url = day ? `/directors/list?day=${day}` : "/directors/list";
    const res = await fetch(url, { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      console.log("Loaded directors:", {
        day: day,
        count: data.directors.length,
        directors: data.directors,
      });

      const sel = document.getElementById("directorSelect");
      if (sel) {
        sel.innerHTML = '<option value="">-- Выберите директора --</option>';
        data.directors.forEach((d) => {
          const opt = document.createElement("option");
          opt.value = d.user_id; // store director user id as value
          opt.dataset.locationId = d.location_id; // store linked location id
          // prefer server-provided name/email fields
          opt.dataset.userName =
            d.user_name || d.name || d.user_email || `Директор #${d.user_id}`;
          const label = `${opt.dataset.userName} — ${d.location_name}`;
          opt.textContent = label;
          sel.appendChild(opt);
        });
        if (data.directors.length > 0) {
          // Try to keep currently selected director if they exist in new list
          let directorToSelect = null;
          if (selectedDirectorUserId) {
            directorToSelect = data.directors.find(
              (d) => String(d.user_id) === String(selectedDirectorUserId),
            );
          }
          // If current director not found, select first director
          if (!directorToSelect) {
            directorToSelect = data.directors[0];
          }

          sel.value = directorToSelect.user_id;
          selectedDirectorUserId = String(directorToSelect.user_id);
          currentLocationId = String(directorToSelect.location_id);
          // load data for initial director selection
          loadAll();
        }
      }
    } else {
      console.error("Failed to load directors, status:", res.status);
    }
  } catch (e) {
    console.error("Ошибка при загрузке директоров:", e);
  }
}

async function loadLocations() {
  try {
    const res = await fetch("/locations/list", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      console.log("Loaded locations:", {
        count: data.locations.length,
        locations: data.locations,
      });

      const sel = document.getElementById("locationSelect");
      if (sel) {
        sel.innerHTML = "";
        data.locations.forEach((l) => {
          const opt = document.createElement("option");
          opt.value = l.id;
          opt.textContent = l.location_name;
          sel.appendChild(opt);
        });
        if (data.locations.length > 0) {
          sel.value = data.locations[0].id;
          currentLocationId = data.locations[0].id;
        }
      } else {
        // if top location select removed, still set default currentLocationId from data
        if (data.locations.length > 0 && !currentLocationId) {
          currentLocationId = data.locations[0].id;
        }
      }
      // also populate assignLocationSelect if present
      const assignSel = document.getElementById("assignLocationSelect");
      if (assignSel) {
        assignSel.innerHTML = "";
        data.locations.forEach((l) => {
          const o = document.createElement("option");
          o.value = l.id;
          o.textContent = l.location_name;
          assignSel.appendChild(o);
        });
      }
    }
  } catch (e) {
    console.error("Ошибка при загрузке локаций:", e);
  }
}

async function loadAllOwners() {
  try {
    const res = await fetch("/owners", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      allOwners = {};
      data.forEach((o) => {
        allOwners[o.id] = o.name;
      });

      console.log("Loaded owners:", { count: data.length, owners: allOwners });

      // Заполняем селект для привязок (assignOwnersSelect) если есть
      const assignSel = document.getElementById("assignOwnersSelect");
      if (assignSel) {
        assignSel.innerHTML = "";
        Object.entries(allOwners).forEach(([id, name]) => {
          const opt = document.createElement("option");
          opt.value = id;
          opt.textContent = name;
          assignSel.appendChild(opt);
        });
      }
    } else {
      console.error("Failed to load owners, status:", res.status);
    }
  } catch (e) {
    console.error("Ошибка при загрузке owners:", e);
  }
}

function updateEditableStatus() {
  // HR и суперпользователь могут редактировать прошедшие дни.
  // Клиентская сторона не блокирует редактирование по дате — сервер проверит права.
  const warning = document.getElementById("warningText");
  if (warning) {
    warning.style.display = "block";
    warning.textContent =
      "HR и суперпользователь могут редактировать прошедшие дни; директор — только текущий день.";
  }
}

async function loadAll() {
  // If a director is selected, prefer the director's linked location
  const directorSel = document.getElementById("directorSelect");

  // ✅ Автоматически выбираем первого директора если ничего не выбрано
  if (directorSel && !directorSel.value && directorSel.options.length > 1) {
    // Пропускаем пустой option (index 0), выбираем первого реального директора
    if (directorSel.options[1]) {
      directorSel.selectedIndex = 1;
    }
  }

  if (directorSel && directorSel.value) {
    const chosen = directorSel.options[directorSel.selectedIndex];
    currentLocationId =
      chosen && chosen.dataset && chosen.dataset.locationId
        ? chosen.dataset.locationId
        : directorSel.value;
  } else {
    const locEl =
      document.getElementById("assignLocationSelect") ||
      document.getElementById("locationSelect");
    currentLocationId = locEl ? locEl.value : currentLocationId;
  }
  const day = document.getElementById("dateFilter").value;
  currentDay = day;

  // ✅ ВАЖНО: если локация не выбрана - ничего не загружаем, просто выходим тихо
  if (!currentLocationId) {
    console.log("Локация не выбрана, пропускаем загрузку");
    return;
  }

  // Load owners for location/day
  // If owners-assignment UI exists, load assignments for this location/day
  try {
    if (
      document.getElementById("assignCurrentList") ||
      document.getElementById("assignOwnersSelect")
    ) {
      await loadOwnerAssignments();
    }
  } catch (e) {
    console.error("Ошибка при загрузке привязок owners", e);
  }

  // Load employees list
  try {
    const res2 = await fetch(
      "/employees/list?day=" + day + "&location_id=" + currentLocationId,
      { credentials: "include" },
    );
    if (res2.ok) {
      const d2 = await res2.json();
      console.log("Loaded employees:", {
        day: day,
        locationId: currentLocationId,
        count: d2.employees.length,
        employees: d2.employees,
      });

      const tbody = document.getElementById("employeesTable");
      if (tbody) {
        tbody.innerHTML = "";

        if (!d2.employees || d2.employees.length === 0) {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td colspan="3" class="text-center text-muted">Нет работников</td>`;
          tbody.appendChild(tr);
        } else {
          d2.employees.forEach((e) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
            <td>${e.name}</td>
            <td>
              <select class="form-select form-select-sm employee-owner-select" data-employee-id="${
                e.id
              }">
                <option value="">-- Не назначен --</option>
              </select>
            </td>
            <td>
              <button class="btn btn-sm btn-success" onclick="saveEmployeeAssignment(${
                e.id
              })">Сохранить</button>
              <button class="btn btn-sm btn-info" onclick="showEmployeeHistory(${
                e.id
              }, '${escapeHtml(e.name)}')">История</button>
            </td>
          `;
            tbody.appendChild(tr);

            // Заполняем селект owners
            const select = tr.querySelector(".employee-owner-select");
            Object.entries(allOwners).forEach(([id, name]) => {
              const opt = document.createElement("option");
              opt.value = id;
              opt.textContent = name;
              select.appendChild(opt);
            });
            // Устанавливаем текущего владельца (если он есть)
            if (e.owner_id) {
              select.value = String(e.owner_id);
            } else {
              select.value = "";
            }
          });
        }
      }
    } else {
      console.error("Failed to load employees, status:", res2.status);
    }
  } catch (e) {
    console.error("Ошибка при загрузке employees:", e);
  }

  // Load stats
  try {
    const res3 = await fetch(
      `/directors/${currentLocationId}/stats?day=${day}`,
      { credentials: "include" },
    );
    if (res3.ok) {
      const d3 = await res3.json();
      const s = d3.stats || {};
      console.log("Loaded stats from server:", {
        locationId: currentLocationId,
        day: day,
        stats: s,
      });

      const arrived_actual = document.getElementById("arrived_actual");
      const expected = document.getElementById("expected");
      const outsourcing = document.getElementById("outsourcing");
      const overtime = document.getElementById("overtime");
      const lunch = document.getElementById("lunch");

      if (arrived_actual) arrived_actual.value = s.arrived_actual || 0;
      if (expected) expected.value = s.expected || 0;
      if (outsourcing) outsourcing.value = s.outsourcing || 0;
      if (overtime) overtime.value = s.overtime || 0;
      if (lunch) lunch.value = s.lunch || 0;
    } else {
      console.error("Failed to load stats, response status:", res3.status);
    }
  } catch (e) {
    console.error("Ошибка при загрузке stats:", e);
  }

  updateEditableStatus();
}

async function saveStats() {
  // Разрешаем сохранять даже для прошлых дней — сервер проверит права

  if (!currentLocationId) {
    showToast("Выберите директора/склад", "error");
    return;
  }

  const arrived_actual = document.getElementById("arrived_actual");
  const expected = document.getElementById("expected");
  const outsourcing = document.getElementById("outsourcing");
  const overtime = document.getElementById("overtime");
  const lunch = document.getElementById("lunch");

  const arrivedValue = parseInt(arrived_actual?.value || 0);
  const expectedValue = parseInt(expected?.value || 0);
  const outsourcingValue = parseInt(outsourcing?.value || 0);
  const overtimeValue = parseInt(overtime?.value || 0);
  const lunchValue = parseInt(lunch?.value || 0);

  // Build query string with all parameters
  const params = new URLSearchParams({
    day: currentDay,
    arrived_actual: arrivedValue,
    expected: expectedValue,
    outsourcing: outsourcingValue,
    overtime: overtimeValue,
    lunch: lunchValue,
  });

  console.log("Saving stats:", {
    locationId: currentLocationId,
    day: currentDay,
    arrived_actual: arrivedValue,
    expected: expectedValue,
    outsourcing: outsourcingValue,
    overtime: overtimeValue,
    lunch: lunchValue,
  });

  try {
    const url = `/directors/${currentLocationId}/stats?${params.toString()}`;
    console.log("Request URL:", url);

    const res = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });

    console.log("Response status:", res.status);

    if (res.ok) {
      const responseData = await res.json();
      console.log("Stats saved successfully, server response:", responseData);
      showToast("Статистика сохранена", "success");
      // Reload data from server after saving
      loadAll();
    } else {
      showToast("Ошибка при сохранении", "error");
    }
  } catch (e) {
    console.error("Ошибка:", e);
  }
}

async function saveOwners() {
  // Разрешаем сохранять даже для прошлых дней — сервер проверит права
  // If assignment select exists, delegate to saveOwnerAssignments
  if (document.getElementById("assignOwnersSelect")) {
    return saveOwnerAssignments();
  }
  showToast("Нет UI для сохранения owners в этой вкладке", "error");
}

async function saveEmployeeAssignment(employeeId) {
  const select = document.querySelector(`[data-employee-id="${employeeId}"]`);
  if (!select) {
    showToast("Не удалось найти элемент для сохранения", "error");
    return;
  }

  const ownerId = select.value ? parseInt(select.value) : null;
  console.log("Saving employee assignment:", {
    employeeId,
    ownerId,
    selectValue: select.value,
    day: currentDay,
  });

  try {
    const res = await fetch(
      `/employees/${employeeId}/assignment?day=${currentDay}`,
      {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ owner_id: ownerId }),
      },
    );

    if (res.ok) {
      const data = await res.json();
      showToast("Назначение сотрудника сохранено", "success");
      console.log("Employee assignment saved:", data);
      loadAll();
    } else {
      const errData = await res.json();
      console.error("Failed to save assignment:", errData);
      showToast(errData.detail || "Ошибка при сохранении", "error");
    }
  } catch (e) {
    console.error("Error saving assignment:", e);
    showToast("Ошибка: " + e.message, "error");
  }
}

async function showEmployeeHistory(employeeId, employeeName) {
  try {
    const res = await fetch(`/employees/${employeeId}/history`, {
      credentials: "include",
    });

    if (!res.ok) {
      showToast("Ошибка при загрузке истории", "error");
      return;
    }

    const data = await res.json();
    const history = data.history || [];

    let historyHtml = `<div class="employee-history">
      <h5>История привязок: ${escapeHtml(employeeName)}</h5>
      <table class="table table-sm table-striped">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Владелец</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>`;

    if (history.length === 0) {
      historyHtml += `<tr><td colspan="3" class="text-center text-muted">История не найдена</td></tr>`;
    } else {
      history.forEach((h) => {
        const ownerName = h.owner_name
          ? escapeHtml(h.owner_name)
          : '<span class="text-muted">Не назначен</span>';
        const statusBadge = h.finalized
          ? '<span class="badge bg-warning">Зафиксирован</span>'
          : '<span class="badge bg-secondary">Активен</span>';
        historyHtml += `<tr><td>${h.day}</td><td>${ownerName}</td><td>${statusBadge}</td></tr>`;
      });
    }

    historyHtml += `</tbody></table></div>`;

    // Используем showPromptModal или создаём свой модал
    const modalEl = document.getElementById("genericModal");
    if (modalEl) {
      const modal = new bootstrap.Modal(modalEl);
      document.getElementById("genericModalTitle").textContent =
        "История привязок работника";
      document.getElementById("genericModalBody").innerHTML = historyHtml;

      // Скрываем кнопку подтверждения
      const confirmBtn = document.getElementById("genericModalConfirm");
      const cancelBtn = document.getElementById("genericModalCancel");
      if (confirmBtn) confirmBtn.style.display = "none";
      if (cancelBtn) cancelBtn.textContent = "Закрыть";

      // Очищаем input
      const input = document.getElementById("genericModalInput");
      if (input) input.style.display = "none";

      modal.show();

      // Восстанавливаем после закрытия
      modalEl.addEventListener(
        "hidden.bs.modal",
        () => {
          if (confirmBtn) confirmBtn.style.display = "block";
          if (input) input.style.display = "block";
        },
        { once: true },
      );
    }
  } catch (e) {
    console.error("Ошибка при загрузке истории:", e);
    showToast("Ошибка при загрузке истории", "error");
  }
}

/* Director Warehouses Management */
let directorWarehousesCache = {};

async function loadDirectorWarehousesManagement() {
  // Загружаем список директоров для селекта
  const directorUserSelect = document.getElementById("directorUserSelect");
  if (!directorUserSelect) return;

  try {
    const res = await fetch("/directors/list", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      const directors = data.directors || [];

      // Очищаем и заполняем селект уникальными директорами
      directorUserSelect.innerHTML =
        '<option value="">-- Выберите директора --</option>';
      const uniqueDirectors = {};
      directors.forEach((d) => {
        if (!uniqueDirectors[d.user_id]) {
          uniqueDirectors[d.user_id] = {
            id: d.user_id,
            name:
              d.user_name || d.name || d.user_email || `Директор #${d.user_id}`,
          };
        }
      });

      Object.values(uniqueDirectors).forEach((d) => {
        const opt = document.createElement("option");
        opt.value = d.id;
        opt.textContent = d.name;
        directorUserSelect.appendChild(opt);
      });

      // Загружаем все склады для кэша
      await loadAllLocationsForDirectorManagement();

      // Добавляем обработчик изменения
      directorUserSelect.addEventListener("change", async () => {
        const userId = directorUserSelect.value;
        if (userId) {
          await loadDirectorWarehouses(parseInt(userId));
        } else {
          clearDirectorWarehousesUI();
        }
      });
    }
  } catch (e) {
    console.error("Ошибка при загрузке списка директоров:", e);
  }
}

async function loadAllLocationsForDirectorManagement() {
  try {
    const res = await fetch("/locations/list", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      directorWarehousesCache = {
        locations: data.locations || [],
        locationMap: {},
      };
      (data.locations || []).forEach((l) => {
        directorWarehousesCache.locationMap[l.id] = l.location_name;
      });
    }
  } catch (e) {
    console.error("Ошибка при загрузке складов:", e);
  }
}

async function loadDirectorWarehouses(userId) {
  const currentList = document.getElementById("directorWarehousesList");
  const availableList = document.getElementById("availableWarehousesList");
  const emptyMsg = document.getElementById("directorWarehousesEmpty");

  if (!currentList || !availableList) return;

  try {
    const res = await fetch(`/directors/${userId}/locations`, {
      credentials: "include",
    });
    if (!res.ok) {
      showToast("Ошибка при загрузке складов директора", "error");
      return;
    }

    const data = await res.json();
    const assignedLocations = (data.locations || []).map((l) => l.location_id);

    // Очищаем списки
    currentList.innerHTML = "";
    availableList.innerHTML = "";

    // Заполняем текущие привязанные склады
    const locations = directorWarehousesCache.locations || [];
    let hasAssigned = false;

    locations.forEach((loc) => {
      if (assignedLocations.includes(loc.id)) {
        hasAssigned = true;
        const item = document.createElement("div");
        item.className =
          "list-group-item d-flex justify-content-between align-items-center";
        item.setAttribute("data-location-id", loc.id);
        item.innerHTML = `
          <div>${escapeHtml(loc.location_name)} <small class="text-muted">#${loc.id}</small></div>
          <div>
            <button class="btn btn-sm btn-outline-danger" onclick="removeDirectorWarehouse(${userId}, ${loc.id})">Отвязать</button>
          </div>
        `;
        currentList.appendChild(item);
      }
    });

    if (hasAssigned) {
      emptyMsg.style.display = "none";
    } else {
      emptyMsg.style.display = "block";
    }

    // Заполняем доступные склады (не привязанные)
    locations.forEach((loc) => {
      if (!assignedLocations.includes(loc.id)) {
        const item = document.createElement("div");
        item.className =
          "list-group-item d-flex justify-content-between align-items-center";
        item.setAttribute("data-location-id", loc.id);
        item.innerHTML = `
          <div>${escapeHtml(loc.location_name)} <small class="text-muted">#${loc.id}</small></div>
          <div>
            <button class="btn btn-sm btn-primary" onclick="addDirectorWarehouse(${userId}, ${loc.id})">Привязать</button>
          </div>
        `;
        availableList.appendChild(item);
      }
    });
  } catch (e) {
    console.error("Ошибка при загрузке складов директора:", e);
  }
}

function clearDirectorWarehousesUI() {
  const currentList = document.getElementById("directorWarehousesList");
  const availableList = document.getElementById("availableWarehousesList");
  const emptyMsg = document.getElementById("directorWarehousesEmpty");

  if (currentList) currentList.innerHTML = "";
  if (availableList) availableList.innerHTML = "";
  if (emptyMsg) emptyMsg.style.display = "block";
}

async function addDirectorWarehouse(userId, locationId) {
  try {
    const res = await fetch(
      `/directors/${userId}/locations?location_id=${locationId}`,
      {
        method: "POST",
        credentials: "include",
      },
    );

    if (res.ok) {
      const data = await res.json();
      showToast(data.message || "Склад успешно привязан", "success");
      await loadDirectorWarehouses(userId);
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || "Ошибка при привязке склада", "error");
    }
  } catch (e) {
    console.error("Ошибка при привязке склада:", e);
    showToast("Ошибка при привязке склада", "error");
  }
}

async function removeDirectorWarehouse(userId, locationId) {
  const ok = await showConfirmModal("Отвязать склад от директора?");
  if (!ok) return;

  try {
    const res = await fetch(`/directors/${userId}/locations/${locationId}`, {
      method: "DELETE",
      credentials: "include",
    });

    if (res.ok) {
      const data = await res.json();
      showToast(data.message || "Склад успешно отвязан", "success");
      await loadDirectorWarehouses(userId);
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || "Ошибка при отвязке склада", "error");
    }
  } catch (e) {
    console.error("Ошибка при отвязке склада:", e);
    showToast("Ошибка при отвязке склада", "error");
  }
}

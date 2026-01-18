document.addEventListener("DOMContentLoaded", () => {
  // Workers
  const createWorkerBtn = document.getElementById("createWorkerBtn");
  if (createWorkerBtn) createWorkerBtn.addEventListener("click", createWorker);

  const workersShowInactive = document.getElementById("workersShowInactive");
  if (workersShowInactive)
    workersShowInactive.addEventListener("change", loadWorkers);

  // Locations
  const createLocationBtn = document.getElementById("createLocationBtn");
  if (createLocationBtn)
    createLocationBtn.addEventListener("click", createLocation);

  const locationsShowInactive = document.getElementById(
    "locationsShowInactive"
  );
  if (locationsShowInactive)
    locationsShowInactive.addEventListener("change", loadLocations);

  // Directors
  const createDirectorBtn = document.getElementById("createDirectorBtn");
  if (createDirectorBtn)
    createDirectorBtn.addEventListener("click", openCreateDirectorModal);

  const directorsShowInactive = document.getElementById(
    "directorsShowInactive"
  );
  if (directorsShowInactive)
    directorsShowInactive.addEventListener("change", loadDirectors);

  // initial load
  loadWorkers();
  loadLocations();
  loadDirectors();
});

async function loadWorkers() {
  const showInactive = document.getElementById("workersShowInactive").checked;
  const list = document.getElementById("workersList");
  list.innerHTML = "Загрузка...";
  try {
    const res = await fetch(
      "/hr_admin/employees?show_inactive=" + (showInactive ? "1" : "0"),
      { credentials: "include" }
    );
    if (!res.ok) return showToast("Не удалось загрузить работников", "error");
    const d = await res.json();
    list.innerHTML = "";
    if (!d.employees || d.employees.length === 0) {
      list.innerHTML = '<div class="text-muted">Нет записей</div>';
      return;
    }
    d.employees.forEach((w) => {
      const el = document.createElement("div");
      el.className =
        "list-group-item d-flex justify-content-between align-items-center";
      
      // Формируем статус и дату увольнения/возвращения
      let statusHtml = "";
      if (!w.is_active) {
        statusHtml = '<span class="badge bg-secondary ms-2">уволен</span>';
        if (w.terminated_at) {
          const terminatedDate = new Date(w.terminated_at).toLocaleDateString('ru-RU');
          statusHtml += `<small class="text-muted ms-2">(${terminatedDate})</small>`;
        }
      } else if (w.rehired_at) {
        const rehiredDate = new Date(w.rehired_at).toLocaleDateString('ru-RU');
        statusHtml = `<small class="text-muted ms-2">Возвращен: ${rehiredDate}</small>`;
      }
      
      el.innerHTML = `<div class="flex-grow-1 me-3 text-truncate"><strong title="${escapeHtml(
        w.name
      )}">${escapeHtml(w.name)}</strong> <small class="text-muted">#${
        w.id
      }</small> ${statusHtml}</div><div>`;
      const btns = [];
      if (w.is_active) {
        btns.push(
          `<button class="btn btn-sm btn-danger" onclick="fireWorker(${w.id})">Уволить</button>`
        );
      } else {
        btns.push(
          `<button class="btn btn-sm btn-success" onclick="reactivateWorker(${w.id})">Вернуть</button>`
        );
      }
      el.innerHTML += btns.join(" ") + "</div>";
      list.appendChild(el);
    });
  } catch (e) {
    console.error(e);
    showToast("Ошибка загрузки работников", "error");
  }
}

async function createWorker() {
  const name = document.getElementById("newWorkerName").value.trim();
  if (!name) return showToast("Введите имя сотрудника", "error");
  try {
    const res = await fetch(
      "/hr_admin/employees?name=" + encodeURIComponent(name),
      { method: "POST", credentials: "include" }
    );
    if (res.ok) {
      document.getElementById("newWorkerName").value = "";
      loadWorkers();
      showToast("Сотрудник создан", "success");
    } else showToast("Ошибка создания", "error");
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

async function fireWorker(id) {
  const ok = await showConfirmModal("Уволить сотрудника?");
  if (!ok) return;
  try {
    const res = await fetch(`/hr_admin/employees/${id}/fire`, {
      method: "POST",
      credentials: "include",
    });
    if (res.ok) {
      loadWorkers();
      showToast("Сотрудник уволен", "success");
    } else showToast("Ошибка", "error");
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

async function reactivateWorker(id) {
  try {
    const res = await fetch(`/hr_admin/employees/${id}/reactivate`, {
      method: "POST",
      credentials: "include",
    });
    if (res.ok) {
      loadWorkers();
      showToast("Сотрудник восстановлен", "success");
    } else {
      loadWorkers();
      showToast("Операция выполнена", "info");
    }
  } catch (e) {
    console.error(e);
    loadWorkers();
  }
}

/* Locations */
async function loadLocations() {
  const showInactive = document.getElementById("locationsShowInactive").checked;
  const list = document.getElementById("locationsList");
  list.innerHTML = "Загрузка...";
  try {
    const res = await fetch(
      "/hr_admin/locations?show_inactive=" + (showInactive ? "1" : "0"),
      { credentials: "include" }
    );
    if (!res.ok) return showToast("Не удалось загрузить склады", "error");
    const d = await res.json();
    list.innerHTML = "";
    const locSel = document.getElementById("newDirectorLocation");
    if (locSel) locSel.innerHTML = "";
    if (!d.locations || d.locations.length === 0) {
      list.innerHTML = '<div class="text-muted">Нет записей</div>';
      return;
    }
    d.locations.forEach((l) => {
      const el = document.createElement("div");
      el.className =
        "list-group-item d-flex justify-content-between align-items-center";
      const status = l.is_active
        ? ""
        : '<span class="badge bg-secondary ms-2">деактивирован</span>';
      el.innerHTML = `<div class="flex-grow-1 me-3 text-truncate"><strong title="${escapeHtml(
        l.location_name
      )}">${escapeHtml(l.location_name)}</strong> <small class="text-muted">#${
        l.id
      }</small> ${status}</div><div>`;
      const btns = [];
      if (l.is_active) {
        btns.push(
          `<button class="btn btn-sm btn-danger" onclick="deactivateLocation(${l.id})">Деактивировать</button>`
        );
      } else {
        btns.push(
          `<button class="btn btn-sm btn-success" onclick="reactivateLocation(${l.id})">Активировать</button>`
        );
      }
      el.innerHTML += btns.join(" ") + "</div>";
      list.appendChild(el);
      if (locSel && l.is_active) {
        const opt = document.createElement("option");
        opt.value = l.id;
        opt.textContent = l.location_name;
        locSel.appendChild(opt);
      }
    });
  } catch (e) {
    console.error(e);
    showToast("Ошибка загрузки складов", "error");
  }
}

async function createLocation() {
  const name = document.getElementById("newLocationName").value.trim();
  if (!name) return showToast("Введите название склада", "error");
  try {
    const res = await fetch(
      "/hr_admin/locations?location_name=" + encodeURIComponent(name),
      { method: "POST", credentials: "include" }
    );
    if (res.ok) {
      document.getElementById("newLocationName").value = "";
      loadLocations();
      showToast("Склад создан", "success");
    } else showToast("Ошибка создания склада", "error");
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

async function deactivateLocation(id) {
  const ok = await showConfirmModal("Деактивировать склад?");
  if (!ok) return;
  try {
    const res = await fetch(`/hr_admin/locations/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (res.ok) {
      loadLocations();
      showToast("Склад деактивирован", "success");
    } else showToast("Ошибка при деактивации", "error");
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

async function reactivateLocation(id) {
  try {
    const res = await fetch(`/hr_admin/locations/${id}/reactivate`, {
      method: "POST",
      credentials: "include",
    });
    if (res.ok) {
      loadLocations();
      showToast("Склад активирован", "success");
    } else showToast("Ошибка при активации", "error");
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

/* Directors */
async function loadDirectors() {
  const showInactiveEl = document.getElementById("directorsShowInactive");
  const listEl = document.getElementById("directorsList");
  if (!showInactiveEl || !listEl) return;

  const showInactive = showInactiveEl.checked;
  listEl.innerHTML = "Загрузка...";
  try {
    const res = await fetch(
      "/hr_admin/directors?show_inactive=" + (showInactive ? "1" : "0"),
      { credentials: "include" }
    );
    if (!res.ok) return showToast("Не удалось загрузить директоров", "error");
    const d = await res.json();
    listEl.innerHTML = "";
    if (!d.directors || d.directors.length === 0) {
      listEl.innerHTML = '<div class="text-muted">Нет записей</div>';
      return;
    }
    d.directors.forEach((dr) => {
      const el = document.createElement("div");
      el.className =
        "list-group-item d-flex justify-content-between align-items-center";
      const status = dr.is_active
        ? ""
        : '<span class="badge bg-secondary ms-2">деактивирован</span>';
      const displayName = dr.name || `user #${dr.user_id}`;
      el.innerHTML = `<div class="flex-grow-1 me-3 text-truncate"><strong title="${escapeHtml(
        displayName
      )}">${escapeHtml(displayName)}</strong> — склад #${
        dr.location_id
      } ${status}</div><div>`;
      const btns = [];
      if (dr.is_active) {
        btns.push(
          `<button class="btn btn-sm btn-danger" onclick="deactivateDirector(${dr.user_id})">Деактивировать</button>`
        );
        btns.push(
          `<button class="btn btn-sm btn-outline-primary ms-2" onclick="editDirectorCredentials(${
            dr.user_id
          }, '${escapeHtml(dr.name || "")}', '${escapeHtml(
            dr.email || ""
          )}')">Изменить учётку</button>`
        );
      } else {
        btns.push(
          `<button class="btn btn-sm btn-success" onclick="reactivateDirector(${dr.user_id})">Активировать</button>`
        );
      }
      el.innerHTML += btns.join(" ") + "</div>";
      listEl.appendChild(el);
    });
  } catch (e) {
    console.error(e);
    showToast("Ошибка загрузки директоров", "error");
  }
}

async function openCreateDirectorModal() {
  // fetch active locations for select options
  try {
    const res = await fetch("/hr_admin/locations?show_inactive=0", {
      credentials: "include",
    });
    if (!res.ok) return showToast("Не удалось загрузить склады", "error");
    const dd = await res.json();
    const opts = (dd.locations || []).map((l) => ({
      value: l.id,
      text: l.location_name,
    }));
    if (opts.length === 0)
      return showToast("Нет активных складов для назначения", "error");

    // generate password immediately so HR sees it and can change if needed
    const genPass = (function gen() {
      // use crypto if available
      try {
        const arr = new Uint8Array(12);
        crypto.getRandomValues(arr);
        return Array.from(arr)
          .map((b) => (b % 36).toString(36))
          .join("");
      } catch (e) {
        return Math.random().toString(36).slice(2, 10);
      }
    })();

    const out = await showFormModal("Создать директора склада", [
      { name: "name", label: "Имя директора", value: "", required: true },
      { name: "email", label: "Email (логин)", value: "", required: true },
      {
        name: "password",
        label: "Пароль (сгенерирован, можно изменить)",
        type: "text",
        value: genPass,
        required: true,
      },
      {
        name: "location_id",
        label: "Склад",
        type: "select",
        options: opts,
        value: opts[0].value,
        required: true,
      },
    ]);
    if (!out) return;
    // validate required fields
    if (!out.email || !out.email.trim())
      return showToast("Email обязателен", "error");
    if (!out.name || !out.name.trim())
      return showToast("Имя обязательно", "error");
    // build request
    const params = new URLSearchParams();
    params.append("name", out.name || "");
    params.append("location_id", out.location_id);
    params.append("email", out.email.trim());
    // always send password (we generate it by default)
    params.append("password", out.password || "");

    const createRes = await fetch(
      "/hr_admin/directors/create_user?" + params.toString(),
      { method: "POST", credentials: "include" }
    );
    if (!createRes.ok) {
      const txt = await createRes.text();
      return showToast("Ошибка создания: " + txt, "error");
    }
    const data = await createRes.json();
    loadDirectors();
    loadLocations();
    if (data.credentials) {
      await showFormModal("Учётные данные директора", [
        { name: "login", label: "Логин", value: data.credentials.login },
        {
          name: "password",
          label: "Пароль (скопируйте и передайте директору)",
          value: data.credentials.password,
        },
      ]);
      showToast("Директор создан и учётные данные показаны", "success");
    } else {
      showToast("Директор создан", "success");
    }
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

async function editDirectorName(userId) {
  const nv = await showPromptModal("Изменить имя директора", "Новое имя", "");
  if (nv === null) return;
  if (!nv.trim()) return showToast("Имя не может быть пустым", "error");
  try {
    const res = await fetch(
      `/hr_admin/directors/${userId}/name?name=${encodeURIComponent(nv)}`,
      { method: "PUT", credentials: "include" }
    );
    if (res.ok) {
      loadDirectors();
      showToast("Имя директора обновлено", "success");
    } else {
      const txt = await res.text();
      showToast("Ошибка обновления: " + txt, "error");
    }
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

async function deactivateDirector(userId) {
  const ok = await showConfirmModal(
    "Деактивировать директора и его учётную запись?"
  );
  if (!ok) return;
  try {
    const res = await fetch(`/hr_admin/directors/${userId}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (res.ok) {
      loadDirectors();
      showToast("Директор деактивирован", "success");
    } else showToast("Ошибка", "error");
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

async function reactivateDirector(userId) {
  try {
    const res = await fetch(`/hr_admin/directors/${userId}/reactivate`, {
      method: "POST",
      credentials: "include",
    });
    if (res.ok) {
      loadDirectors();
      showToast("Директор активирован", "success");
    } else showToast("Ошибка", "error");
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

async function editDirectorCredentials(userId, encName, encEmail) {
  const currentName = decodeURIComponent(encName || "");
  const currentEmail = decodeURIComponent(encEmail || "");
  const out = await showFormModal("Редактировать учётку директора", [
    { name: "name", label: "Имя", value: currentName },
    { name: "email", label: "Email (логин)", value: currentEmail },
    {
      name: "password",
      label: "Новый пароль (оставьте пустым чтобы не менять)",
      type: "password",
      value: "",
    },
  ]);
  if (!out) return;
  const params = new URLSearchParams();
  if (out.name && out.name.trim()) params.append("name", out.name.trim());
  if (out.email && out.email.trim()) params.append("email", out.email.trim());
  if (out.password && out.password.trim())
    params.append("password", out.password.trim());
  if ([...params].length === 0) return showToast("Нет изменений", "info");
  try {
    const res = await fetch(
      `/hr_admin/directors/${userId}/credentials?` + params.toString(),
      {
        method: "PUT",
        credentials: "include",
      }
    );
    if (res.ok) {
      loadDirectors();
      showToast("Данные директора обновлены", "success");
    } else {
      const txt = await res.text();
      showToast("Ошибка обновления: " + txt, "error");
    }
  } catch (e) {
    console.error(e);
    showToast("Ошибка", "error");
  }
}

function escapeHtml(s) {
  if (!s) return "";
  return s.replace(/'/g, "\\'").replace(/\"/g, '\\"');
}

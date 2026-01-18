let currentDay = null;
let todayDate = null;
let directorData = null;
let currentStats = null;
let allStatsData = {}; // Кеш статистики всех дней

document.addEventListener("DOMContentLoaded", async () => {
  todayDate = new Date().toISOString().slice(0, 10);
  currentDay = todayDate;
  document.getElementById("dateNavigator").value = currentDay;
  document.getElementById("dateNavigator").max = todayDate;

  // Загружаем данные панели директора
  await loadDashboard();

  // Обработчик смены даты
  document.getElementById("dateNavigator").addEventListener("change", (e) => {
    currentDay = e.target.value;
    loadDashboard();
  });
});

async function loadDashboard() {
  try {
    const res = await fetch("/directors/director/dashboard", {
      credentials: "include",
    });

    if (!res.ok) {
      if (res.status === 403) {
        showToast("У вас нет доступа к этой странице", "error");
        window.location.href = "/login";
      } else {
        showToast("Ошибка при загрузке данных", "error");
      }
      return;
    }

    directorData = await res.json();

    // Отображаем информацию о складе
    const locationNameEl = document.getElementById("locationName");
    const locationInfoEl = document.getElementById("locationInfo");
    if (locationNameEl)
      locationNameEl.textContent = directorData.location.location_name;
    if (locationInfoEl)
      locationInfoEl.textContent = `Ваш склад • Сегодня: ${directorData.today}`;

    // Отображаем владельцев
    displayOwners();

    // Отображаем работников по дням
    displayEmployeesByDay();

    // Загружаем и отображаем статистику
    await displayStats();
  } catch (e) {
    console.error("Ошибка при загрузке панели директора:", e);
    showToast("Ошибка при загрузке данных", "error");
  }
}

function displayOwners() {
  const container = document.getElementById("ownersList");
  if (!container) return;

  if (!directorData.owners || directorData.owners.length === 0) {
    container.innerHTML =
      '<div class="no-data">Нет привязанных владельцев</div>';
    return;
  }

  container.innerHTML = directorData.owners
    .map(
      (owner) => `<span class="owner-badge">${escapeHtml(owner.name)}</span>`
    )
    .join("");
}

function displayEmployeesByDay() {
  const container = document.getElementById("employeesContainer");
  if (!container) return;

  if (
    !directorData.employees_by_day ||
    Object.keys(directorData.employees_by_day).length === 0
  ) {
    container.innerHTML =
      '<div class="card"><div class="card-body"><div class="no-data">Нет данных о работниках</div></div></div>';
    return;
  }

  // Получаем работников для выбранного дня
  let employees = directorData.employees_by_day[currentDay] || [];

  // Фильтруем только работников, которые привязаны к владельцам директора
  // ИЛИ которые были уволнены в этот день
  const ownerIds = new Set((directorData.owners || []).map((o) => o.id));
  employees = employees.filter(
    (emp) => (emp.owner_id && ownerIds.has(emp.owner_id)) || emp.is_fired_today
  );

  if (employees.length === 0) {
    container.innerHTML =
      '<div class="card"><div class="card-body"><div class="no-data">Нет работников, привязанных к вашим владельцам на выбранный день</div></div></div>';
    return;
  }

  let html = `<div class="employees-grid">`;

  employees.forEach((emp) => {
    const isFiredToday = emp.is_fired_today === true;
    const ownerName = !isFiredToday
      ? (directorData.owners.find((o) => o.id == emp.owner_id)?.name ||
          "Не назначен")
      : "Уволнен";

    // Проверяем, был ли сотрудник уволнен на эту дату
    const cardClasses = isFiredToday ? "employee-card employee-card-fired" : "employee-card";
    const firedBadge = isFiredToday ? '<span class="badge bg-danger ms-2">УВОЛЕН</span>' : "";

    html += `
      <div class="${cardClasses}">
        <div class="employee-name">
          <i class="bi bi-person"></i> ${escapeHtml(emp.name)} ${firedBadge}
        </div>
        <div class="employee-owner">
          ${escapeHtml(ownerName)}
        </div>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
}

async function displayStats() {
  const editableStatsSection = document.getElementById("editableStatsSection");
  const statsViewContainer = document.getElementById("statsViewContainer");
  const isToday = currentDay === directorData.today;

  // Загружаем статистику для выбранного дня
  try {
    const res = await fetch(`/directors/me/stats?day=${currentDay}`, {
      credentials: "include",
    });

    if (!res.ok) {
      console.error("Ошибка при загрузке статистики:", res.status);
      statsViewContainer.innerHTML =
        '<div class="card"><div class="card-body"><div class="no-data">Ошибка при загрузке статистики</div></div></div>';
      return;
    }

    const data = await res.json();
    currentStats = data.stats;
    allStatsData[currentDay] = data.stats;

    if (isToday) {
      // Показываем форму редактирования только для сегодня
      if (editableStatsSection) {
        editableStatsSection.style.display = "block";
      }

      if (data.stats) {
        const arrivedEl = document.getElementById("arrived_actual");
        const expectedEl = document.getElementById("expected");
        const outsourcingEl = document.getElementById("outsourcing");
        const overtimeEl = document.getElementById("overtime");
        const lunchEl = document.getElementById("lunch");

        if (arrivedEl) arrivedEl.value = data.stats.arrived_actual || 0;
        if (expectedEl) expectedEl.value = data.stats.expected || 0;
        if (outsourcingEl) outsourcingEl.value = data.stats.outsourcing || 0;
        if (overtimeEl) overtimeEl.value = data.stats.overtime || 0;
        if (lunchEl) lunchEl.value = data.stats.lunch || 0;
      } else {
        const arrivedEl = document.getElementById("arrived_actual");
        const expectedEl = document.getElementById("expected");
        const outsourcingEl = document.getElementById("outsourcing");
        const overtimeEl = document.getElementById("overtime");
        const lunchEl = document.getElementById("lunch");

        if (arrivedEl) arrivedEl.value = 0;
        if (expectedEl) expectedEl.value = 0;
        if (outsourcingEl) outsourcingEl.value = 0;
        if (overtimeEl) overtimeEl.value = 0;
        if (lunchEl) lunchEl.value = 0;
      }
    } else {
      if (editableStatsSection) {
        editableStatsSection.style.display = "none";
      }
    }

    // Загружаем и показываем статистику всех дней
    await loadAllStatsForView();
  } catch (e) {
    console.error("Ошибка при загрузке статистики:", e);
    statsViewContainer.innerHTML =
      '<div class="card"><div class="card-body"><div class="no-data">Ошибка при загрузке</div></div></div>';
  }
}

async function loadAllStatsForView() {
  const statsViewContainer = document.getElementById("statsViewContainer");
  if (!statsViewContainer) return;

  // Получаем все дни
  const days = Object.keys(directorData.employees_by_day).sort().reverse();

  if (days.length === 0) {
    statsViewContainer.innerHTML =
      '<div class="card"><div class="card-body"><div class="no-data">Нет данных</div></div></div>';
    return;
  }

  let html = `<div class="stats-view-grid">`;

  for (const day of days) {
    // Получаем статистику из кеша или загружаем
    if (!allStatsData[day]) {
      try {
        const res = await fetch(`/directors/me/stats?day=${day}`, {
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          allStatsData[day] = data.stats;
        }
      } catch (e) {
        console.error(`Ошибка загрузки статистики для ${day}:`, e);
      }
    }

    const stats = allStatsData[day];
    const dateObj = new Date(day + "T00:00:00");
    const dayLabel = dateObj.toLocaleDateString("ru-RU", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    const isToday = day === directorData.today;

    html += `
      <div class="stat-card ${isToday ? "today" : ""}">
        <div class="stat-card-date-header">${dayLabel}${
      isToday ? ' <i class="bi bi-star-fill" style="color: #ffc107;"></i>' : ""
    }</div>
        <div class="stat-card-rows">
          <div class="stat-row">
            <span class="stat-label">Прибыло</span>
            <span class="stat-value">${stats?.arrived_actual || 0}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Ожидалось</span>
            <span class="stat-value">${stats?.expected || 0}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Обед</span>
            <span class="stat-value">${stats?.lunch || 0}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Аутсорсинг</span>
            <span class="stat-value">${stats?.outsourcing || 0}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Переработки</span>
            <span class="stat-value">${stats?.overtime || 0}</span>
          </div>
        </div>
      </div>
    `;
  }

  html += `</div>`;
  statsViewContainer.innerHTML = html;
}

async function saveStats() {
  const today = directorData.today;
  if (currentDay !== today) {
    showToast("Можно редактировать только текущий день", "error");
    return;
  }

  const arrivedEl = document.getElementById("arrived_actual");
  const expectedEl = document.getElementById("expected");
  const outsourcingEl = document.getElementById("outsourcing");
  const overtimeEl = document.getElementById("overtime");
  const lunchEl = document.getElementById("lunch");

  if (!arrivedEl || !expectedEl || !outsourcingEl || !overtimeEl || !lunchEl) {
    showToast("Не все элементы формы найдены", "error");
    return;
  }

  const arrivedValue = parseInt(arrivedEl.value || 0);
  const expectedValue = parseInt(expectedEl.value || 0);
  const outsourcingValue = parseInt(outsourcingEl.value || 0);
  const overtimeValue = parseInt(overtimeEl.value || 0);
  const lunchValue = parseInt(lunchEl.value || 0);

  // Build query string with all parameters
  const params = new URLSearchParams({
    day: today,
    arrived_actual: arrivedValue,
    expected: expectedValue,
    outsourcing: outsourcingValue,
    overtime: overtimeValue,
    lunch: lunchValue,
  });

  try {
    const url = `/directors/me/stats?${params.toString()}`;
    const res = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });

    if (res.ok) {
      showToast("✅ Статистика сохранена", "success");
      // Перезагружаем только статистику, не всю страницу
      await displayStats();
    } else {
      const errorData = await res.json().catch(() => ({}));
      showToast(
        "❌ Ошибка при сохранении: " +
          (errorData.detail || "Неизвестная ошибка"),
        "error"
      );
    }
  } catch (e) {
    console.error("Ошибка при сохранении статистики:", e);
    showToast("❌ Ошибка при сохранении", "error");
  }
}

function previousDay() {
  const currentDate = new Date(currentDay);
  currentDate.setDate(currentDate.getDate() - 1);
  const newDay = currentDate.toISOString().slice(0, 10);

  // Не позволяем идти дальше чем на 5 дней назад
  const maxPrevDate = new Date();
  maxPrevDate.setDate(maxPrevDate.getDate() - 4);
  const maxPrevDateStr = maxPrevDate.toISOString().slice(0, 10);

  if (newDay >= maxPrevDateStr) {
    currentDay = newDay;
    const dateNav = document.getElementById("dateNavigator");
    if (dateNav) dateNav.value = currentDay;
    loadDashboard();
  } else {
    showToast("Можно просматривать только последние 5 дней", "error");
  }
}

function nextDay() {
  const currentDate = new Date(currentDay);
  currentDate.setDate(currentDate.getDate() + 1);
  const newDay = currentDate.toISOString().slice(0, 10);

  // Не позволяем идти дальше чем на сегодня
  if (newDay <= todayDate) {
    currentDay = newDay;
    const dateNav = document.getElementById("dateNavigator");
    if (dateNav) dateNav.value = currentDay;
    loadDashboard();
  } else {
    showToast("Нельзя просматривать будущие дни", "error");
  }
}

function logout() {
  if (confirm("Вы уверены, что хотите выйти?")) {
    window.location.href = "/logout";
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

function switchTab(tabName) {
  // Скрываем все вкладки
  document.querySelectorAll(".tab-content").forEach((tab) => {
    tab.classList.remove("active");
  });

  // Убираем активный класс со всех кнопок
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("active");
  });

  // Показываем выбранную вкладку
  const selectedTab = document.getElementById(tabName + "Tab");
  if (selectedTab) {
    selectedTab.classList.add("active");
  }

  // Активируем соответствующую кнопку
  const selectedBtn = document.getElementById(tabName + "TabBtn");
  if (selectedBtn) {
    selectedBtn.classList.add("active");
  }
}
async function showEmployeeHistory(employeeId, employeeName) {
  try {
    // Обновляем заголовок модального окна
    const modalTitle = document.getElementById("employeeHistoryModalLabel");
    if (modalTitle) {
      modalTitle.textContent = `История привязок: ${escapeHtml(employeeName)}`;
    }

    // Показываем модальное окно
    const modal = new bootstrap.Modal(
      document.getElementById("employeeHistoryModal")
    );
    modal.show();

    // Загружаем историю
    const res = await fetch(`/employees/${employeeId}/history`, {
      credentials: "include",
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error(
        "Failed to load history, status:",
        res.status,
        "response:",
        errorText
      );
      document.getElementById(
        "historyContent"
      ).innerHTML = `<div class="alert alert-danger">
        <strong>Ошибка ${res.status}:</strong> ${res.statusText}
      </div>`;
      return;
    }

    const data = await res.json();
    const history = data.history || [];

    let historyHtml = `<div class="employee-history">`;

    if (history.length === 0) {
      historyHtml += `<div class="alert alert-info" role="alert">
        <i class="bi bi-info-circle"></i> История привязок не найдена
      </div>`;
    } else {
      historyHtml += `<table class="table table-sm table-hover">
        <thead class="table-light">
          <tr>
            <th><i class="bi bi-calendar"></i> Дата</th>
            <th><i class="bi bi-person"></i> Владелец</th>
            <th><i class="bi bi-check-circle"></i> Статус</th>
          </tr>
        </thead>
        <tbody>`;

      history.forEach((h) => {
        const ownerName = h.owner_name
          ? escapeHtml(h.owner_name)
          : '<span class="text-muted">Не назначен</span>';
        let statusBadge = "";

        if (h.finalized) {
          statusBadge =
            '<span class="badge bg-warning text-dark"><i class="bi bi-lock"></i> Зафиксирован</span>';
        } else {
          statusBadge =
            '<span class="badge bg-info"><i class="bi bi-pencil"></i> Активен</span>';
        }

        historyHtml += `<tr>
          <td><code>${h.day}</code></td>
          <td>${ownerName}</td>
          <td>${statusBadge}</td>
        </tr>`;
      });

      historyHtml += `</tbody></table>`;
    }

    historyHtml += `</div>`;

    // Вставляем содержимое в модальное окно
    document.getElementById("historyContent").innerHTML = historyHtml;
  } catch (e) {
    console.error("Ошибка при загрузке истории:", e);
    document.getElementById(
      "historyContent"
    ).innerHTML = `<div class="alert alert-danger">
      <strong>Ошибка:</strong> ${escapeHtml(e.message)}
    </div>`;
  }
}

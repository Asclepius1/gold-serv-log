async function ButtonStatus(buttonId) {
  const response = await fetch(`/files/button_status/${buttonId}`, {
    method: "GET",
    credentials: "include",
  });
  const data = await response.json();

  const attemptsElement = document.getElementById(`attempts_${buttonId}`);
  if (attemptsElement) {
    attemptsElement.innerText = data.attempts_left;
  }

  const timeRemainingElement = document.getElementById(
    `timeRemaining_${buttonId}`,
  );
  if (!timeRemainingElement) {
    console.error(`Element with ID timeRemaining_${buttonId} not found`);
    return;
  }

  if (data.attempts_left === 0) {
    timeRemainingElement.innerText = "";
    document.getElementById(`reloadBtn`).disabled = true;
  } else if (data.last_press_time > 0) {
    let timeRemaining = Math.max(
      0,
      data.default_time_limit - (Date.now() / 1000 - data.last_press_time),
    );
    startCountdown(buttonId, timeRemaining);
  } else {
    timeRemainingElement.innerText = "";
    document.getElementById(`reloadBtn`).disabled = data.attempts_left === 0;
  }
}

function startCountdown(buttonId, time) {
  if (time <= 0) {
    document.getElementById(`timeRemaining_${buttonId}`).innerText = "";
    document.getElementById(`reloadBtn`).disabled = false;
    return;
  }

  document.getElementById(`reloadBtn`).disabled = true;
  let interval = setInterval(() => {
    time--;
    if (time <= 0) {
      clearInterval(interval);
      document.getElementById(`timeRemaining_${buttonId}`).innerText = "";
      document.getElementById(`reloadBtn`).disabled = false;
    } else {
      let hours = Math.floor(time / 3600);
      let minutes = Math.floor((time % 3600) / 60);
      let seconds = Math.floor(time % 60);
      document.getElementById(`timeRemaining_${buttonId}`).innerText =
        `${hours}ч ${minutes}м ${seconds}с`;
    }
  }, 1000);
}

async function pressButton(buttonId) {
  const response = await fetch(`/files/press_button/${buttonId}`, {
    method: "POST",
    credentials: "include",
  });
  const data = await response.json();
  console.log(data.message);
  ButtonStatus(buttonId);
}

async function getFilesByOwnerId(id) {
  const response = await fetch(`/files/${id}`, {
    method: "GET",
    credentials: "include",
  });
  if (response.ok) {
    const files = await response.json();
    return files;
  }
}

async function reloadOwnerFilesById(path, id) {
  document.getElementById("fileTable").innerHTML = "";
  const spinner = document.getElementById("spinner");
  spinner.style.display = "block";

  try {
    pressButton(id);

    const response = await fetch(`/files/upload/?owner_id=${id}`, {
      method: "POST",
      credentials: "include",
    });

    console.log(
      `[LOAD_FILES] Статус ответа: ${response.status} ${response.statusText}`,
    );

    if (!response.ok) {
      // Скрываем спиннер при ошибке
      spinner.style.display = "none";

      try {
        const errorData = await response.text();
        console.error("[LOAD_FILES] Ошибка от сервера:", errorData);
        showError(errorData || "Неизвестная ошибка");
      } catch (parseError) {
        console.error("[LOAD_FILES] Не удалось распарсить ошибку:", parseError);
        showError(`Ошибка ${response.status}: ${response.statusText}`);
      }
      return;
    }

    // Успешный ответ
    const data = await response.json();
    console.log("[LOAD_FILES] Файлы успешно загружены:", data);

    // Загружаем файлы в таблицу
    await loadFiles((path = path), (id = id));
  } catch (error) {
    spinner.style.display = "none";
    console.error("[LOAD_FILES] Ошибка при загрузке файлов:", error);
    showError(`Ошибка: ${error.message}`);
  }
}

function showError(message) {
  const errorAlert = document.getElementById("errorAlert");
  const errorUserMessage = document.getElementById("errorUserMessage");
  const errorDevMessage = document.getElementById("errorDevMessage");

  // Разбиваем сообщение по разделителю |||
  const parts = message.split("|||");

  if (parts.length >= 2) {
    errorUserMessage.textContent = parts[0].trim();
    errorDevMessage.textContent = parts[1].trim();
  } else {
    // Fallback если разделителя нет
    errorUserMessage.textContent = message;
    errorDevMessage.textContent = "⚠️ UNKNOWN_ERROR";
  }

  errorAlert.removeAttribute("hidden");

  // Автоматически скрываем через 12 сек
  setTimeout(() => {
    errorAlert.setAttribute("hidden", "");
  }, 12000);
}

async function downloadFilesById(file_id) {
  const response = await fetch(`/files/download/${file_id}`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`Ошибка загрузки файла: ${response.statusText}`);
  }

  // Получаем имя файла из заголовков
  const contentDisposition = response.headers.get("Content-Disposition");
  let filename = "downloaded_file";
  if (contentDisposition) {
    let match = contentDisposition.match(/filename\*?=(?:UTF-8'')?(.+)/);
    if (match) {
      filename = decodeURIComponent(match[1]).replace(/["']/g, "");
    }
  }

  // Убираем префикс "utf-8" (если есть)
  filename = filename.replace(/^utf-8/i, "");

  // Читаем тело ответа как Blob
  const blob = await response.blob();

  // Создаем ссылку для скачивания
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  // Освобождаем память
  window.URL.revokeObjectURL(url);
}

async function loadFiles(path, id) {
  const table = document.getElementById("fileTable");
  const spinner = document.getElementById("spinner");
  spinner.style.display = "block";
  table.innerHTML = "";
  // document.getElementById("fileBtns").style.display = path ? "block" : "none";

  let files = [];
  try {
    const reloadItems = document.getElementById("reloadItems");
    reloadItems.innerHTML = "";
    reloadItems.innerHTML = `
        <span id="timeRemaining_${id}" timer>-</span>
        <button class="btn btn-secondary mb-2" id="reloadBtn" onclick="reloadOwnerFilesById(path='${path}', id=${id})" disabled >🔄 Обновить <span id="attempts_${id}">-</span></button>
        `;

    ButtonStatus(id);
    files = (await getFilesByOwnerId(id)) || [];

    // Заполняем таблицу
    files.forEach((item, index) => {
      let row = `<tr>
                <td>📄 ${item.name}</td>
                <td>${item.date ? item.date : "-"}</td>
                <td>
                    <button class="btn btn-sm btn-success" onclick="downloadFilesById(${item.id})">Скачать</button>
                </td>
            </tr>`;

      table.innerHTML += row;
    });
  } catch (error) {
    console.error("Ошибка загрузки файлов:", error);
  } finally {
    // Скрываем спиннер после загрузки
    spinner.style.display = "none";
  }
}

async function getOwnerName(ownerId) {
  const response = await fetch(`/owners/${ownerId}`, {
    method: "GET",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Ошибка авторизации");
  }
  const ownerData = await response;
  return ownerData.name;
}

async function startLoad() {
  try {
    const response = await fetch("/users/me", {
      method: "GET",
      credentials: "include", // ВАЖНО: Отправляет куки с запросом
    });

    if (!response.ok) {
      throw new Error("Ошибка авторизации");
    }

    const userData = await response.json();
    const ownerId = userData.owners_id;
    const ownerName = await getOwnerName(ownerId);
    loadFiles(ownerName, ownerId);

    return null;
  } catch (error) {
    console.error("Ошибка при получении данных пользователя:", error);
    return null;
  }
}

// Получаем данные пользователя
startLoad();

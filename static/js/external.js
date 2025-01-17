async function ButtonStatus(buttonId) {
    const response = await fetch(`/files/button_status/${buttonId}`,{
        method: 'GET',
        credentials: 'include',
    });
    const data = await response.json();

    document.getElementById(`attempts_${buttonId}`).innerText = data.attempts_left;

    if (data.last_press_time > 0) {
        let timeRemaining = Math.max(0, 14400 - (Date.now() / 1000 - data.last_press_time));
        startCountdown(buttonId, timeRemaining);
    } else {
        document.getElementById(`timeRemaining_${buttonId}`).innerText = "";
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
            document.getElementById(`timeRemaining_${buttonId}`).innerText = `${hours}ч ${minutes}м ${seconds}с`;
        }
    }, 1000);
}

async function pressButton(buttonId) {
    const response = await fetch(`/files/press_button/${buttonId}`,{
        method: 'POST',
        credentials: 'include',
    });
    const data = await response.json();
    console.log(data.message);
    ButtonStatus(buttonId);
}

async function getFilesByOwnerId(id) {
    const response = await fetch(`/files/${id}`, {
        method: 'GET',
        credentials: 'include',
    });
    if (response.ok) {
        const files = await response.json();
        return files
    }
}

async function reloadOwnerFilesById(path, id) {
    pressButton(id)
    const response = await fetch(`/files/upload/?owner_id=${id}`, {
        method: 'POST',
        credentials: 'include',
    })

    if (!response.ok) {
        const errorData = await response.json();
        console.error("Ошибка загрузки файлов:", errorData.detail);
    } else {
        const data = await response.json();
        console.log("Файл успешно загружен:", data.message);
        loadFiles(path=path, id=id);
    }
}

async function downloadFilesById(file_id) {
    const response = await fetch(`/files/download/${file_id}`, {
        method: 'GET',
        credentials: 'include'
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
        reloadItems.innerHTML = '';
        reloadItems.innerHTML = `
        <span id="timeRemaining_${id}" timer>-</span>
        <button class="btn btn-secondary mb-2" id="reloadBtn" onclick="reloadOwnerFilesById(path='${path}', id=${id})" disabled >🔄 Обновить <span id="attempts_${id}">-</span></button>
        `;
        
        ButtonStatus(id);
        files = await getFilesByOwnerId(id) || [];

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
    const response = await fetch(`/owners/${ownerId}`,{
        method: 'GET',
        credentials: 'include'
    })
    if (!response.ok) {
        throw new Error("Ошибка авторизации");
    }
    const ownerData = await response
    return ownerData.name
}

async function startLoad() {
    try {
        const response = await fetch("/users/me", {
            method: "GET",
            credentials: "include" // ВАЖНО: Отправляет куки с запросом
        });

        if (!response.ok) {
            throw new Error("Ошибка авторизации");
        }

        const userData = await response.json();
        const ownerId = userData.owners_id
        const ownerName = await getOwnerName(ownerId)
        loadFiles(ownerName, ownerId)

        return null
    } catch (error) {
        console.error("Ошибка при получении данных пользователя:", error);
        return null;
    }
}

// Получаем данные пользователя
startLoad();
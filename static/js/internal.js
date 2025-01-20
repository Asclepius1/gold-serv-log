async function ButtonStatus(buttonId) {
    const response = await fetch(`/files/button_status/${buttonId}`,{
        method: 'GET',
        credentials: 'include',
    });
    const data = await response.json();

    document.getElementById(`attempts_${buttonId}`).innerText = data.attempts_left;

    if (data.attempts_left == 0){
        document.getElementById(`timeRemaining_${buttonId}`).innerText = "";
        document.getElementById(`reloadBtn`).disabled = true;
    }
    else if (data.last_press_time > 0) {
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


async function getOwners(){
    const response = await fetch('/owners', {
        method: 'GET',
        credentials: 'include',
    });

    if (response.ok) {
        const owners = await response.json();
        return owners
    }
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

async function loadFiles(path = "", id = null) {
    const table = document.getElementById("fileTable");
    const spinner = document.getElementById("spinner");
    spinner.style.display = "block";
    table.innerHTML = "";
    document.getElementById("fileBtns").style.display = path ? "block" : "none";

    let files = [];
    try {
        if (!id) {
            files = await getOwners() || [];
        } else {
            const reloadItems = document.getElementById("reloadItems");
            reloadItems.innerHTML = '';
            reloadItems.innerHTML = `
            <span id="timeRemaining_${id}" timer>-</span>
            <button class="btn btn-secondary mb-2" id="reloadBtn" onclick="reloadOwnerFilesById(path='${path}', id=${id})" disabled >🔄 Обновить <span id="attempts_${id}">-</span></button>
            `;
            
            ButtonStatus(id);
            files = await getFilesByOwnerId(id) || [];
        }

        // Заполняем таблицу
        files.forEach((item, index) => {
            let row = `<tr>
                <td>${item.type === "file" ? "📄" : "📁"} ${item.name}</td>
                <td>${item.date ? item.date : "-"}</td>
                <td>
                    ${item.type !== "file"
                        ? `<button class="btn btn-sm btn-primary" onclick="loadFiles(path='${item.name}', id=${item.id})">Открыть</button>`
                        : `<button class="btn btn-sm btn-success" onclick="downloadFilesById(${item.id})">Скачать</button>`
                    }
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

document.getElementById("backBtn").addEventListener("click", () => {
    loadFiles();
});

loadFiles();
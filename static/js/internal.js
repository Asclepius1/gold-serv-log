const dummyData = {
    "": [
        { "name": "ALS", "type": "folder", "date": "15.01.2025 14:12" },
        { "name": "BDS", "type": "folder", "date": "15.01.2025 14:12" },
    ],
    "ALS": [
        { "name": "log1.xlsx", "type": "file", "date": "15.01.2025 14:12" },
        { "name": "log2.xlsx", "type": "file", "date": "15.01.2025 14:12" }
    ],
    "BDS": [
        { "name": "docker-compose.xlsx", "type": "file", "date": "15.01.2025 14:12" }
    ]
};

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
    console.log(response)
    if (response.ok) {
        const files = await response.json();
        return files
    }
}

async function reloadOwnerFilesById(id) {
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
        const match = contentDisposition.match(/filename\*?=(?:UTF-8'')?(.+)/);
        if (match) {
            filename = decodeURIComponent(match[1].replace(/["']/g, ""));
        }
    }

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
    console.log(path)
    document.getElementById("fileBtns").style.display = path ? "block" : "none";

    // const files = dummyData[path] || [];
    let files = [];
    try {
        if (!id) {
            files = await getOwners() || [];
        } else {
            document.getElementById("reloadBtn").onclick = function() {
                reloadOwnerFilesById(id);
            };
            files = await getFilesByOwnerId(id) || [];
            console.log(files);
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
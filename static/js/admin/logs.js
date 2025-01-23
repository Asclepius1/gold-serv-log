
let currentSort = { column: "datetime", order: "desc" };
let selectedDateRange = null;
let color = null;

async function saveFilters() {
    const filters = {
        id: document.getElementById("filter-id").value.trim(),
        owner: document.getElementById("filter-owner").value.trim(),
        message: document.getElementById("filter-message").value.trim(),
        dateFrom: selectedDateRange?.from || null,
        dateTo: selectedDateRange?.to || null,
        errorType: document.getElementById("filter-error-type").value.trim(),
        currentSort: currentSort || { column: "datetime", order: "desc" },
        color: color || null,
    };
    await fetch("/logs/filters", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify(filters)
    });
    loadLogs()
}




document.addEventListener("DOMContentLoaded", function () {
    // Прослушиваем изменения в полях фильтров
    document.getElementById("filter-id").addEventListener("input", () => saveFilters());
    document.getElementById("filter-owner").addEventListener("input", () => saveFilters());
    document.getElementById("filter-message").addEventListener("input", () => saveFilters());
    document.getElementById("filter-error-type").addEventListener("input", () => saveFilters());

    document.getElementById("date-range-selector").addEventListener("click", function () {
        const startDate = document.getElementById("start-date").value;
        const endDate = document.getElementById("end-date").value;

        if (startDate && endDate) {
            selectedDateRange = { from: startDate, to: endDate };
            saveFilters();
        } else {
            alert("Пожалуйста, выберите оба диапазона дат.");
        }
    });
});

function selectColor(selectedColor){
    color = selectedColor;
    saveFilters();
};

function setToInputCurrentValues(filter){
    document.getElementById("filter-id").value = filter.id;
    document.getElementById("filter-owner").value = filter.owner;
    document.getElementById("filter-message").value = filter.message;
    document.getElementById("filter-error-type").value = filter.errorType;
    document.getElementById("start-date").value = filter.dateFrom;
    document.getElementById("end-date").value = filter.dateTo;
    color = filter.color;
    currentSort = filter.currentSort;
}

function loadAutoRefreshCheckbox(){
    fetch("/logs/get_autorefresh")
    .then(response => response.json())
    .then(data => {
        document.getElementById("autorefresh-checkbox").checked = data.autorefresh;
    });
}

function toggleAutorefresh(checkbox){
    const state = checkbox.checked; // Получаем состояние чекбокса
    console.log("Автообновление:", state ? "Включено" : "Отключено");
    fetch(`/logs/set_autorefresh?state=${state}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        // params: {
        //     "state": state,
        // }
        // body: JSON.stringify({state: state})
    })
    .then(response => response.json())
    .then(data => {
        console.log('Статус обновления:', data);
    })
    .catch(error => console.error('Ошибка:', error))
}

async function loadLogs(page = 1) {
    // const sortColumn = currentSort.column || "datetime";
    // const sortOrder = currentSort.order || "desc";
    const pageSize = 50;
        
    const filters = await fetch("/logs/filters", {
        method: "GET",
        credentials: "include"
    }).then(res => res.json());

    loadAutoRefreshCheckbox();
    setToInputCurrentValues(filters);

    // Формируем URL с параметрами
    const params = new URLSearchParams({
        page,
        page_size: pageSize,
        // sort_by: sortColumn,
        // sort_order: sortOrder
    });

    if (filters.id) params.append("log_id", filters.id);
    if (filters.owner) params.append("owner_name", filters.owner);
    if (filters.message) params.append("message", filters.message);
    if (filters.dateFrom) params.append("start_date", filters.dateFrom);
    if (filters.dateTo) params.append("end_date", filters.dateTo);
    if (filters.errorType) params.append("error_type", filters.errorType);
    if (filters.color) params.append("color", filters.color);
    if (filters.currentSort) params.append("sort_by", filters.currentSort.column);
    if (filters.currentSort) params.append("sort_order", filters.currentSort.order);

    try {
        const response = await fetch(`/logs?${params.toString()}`, {
            method: "GET",
            credentials: "include",
        });

        const data = await response.json();
        const tableBody = document.getElementById("logsTable");
        tableBody.innerHTML = "";

        data.data.forEach(log => {
            const row = document.createElement("tr");
            if(log.color == 'red') row.classList.add("table-danger")
            else if(log.color == 'yellow') row.classList.add("table-warning")
            else row.classList.add("table-success")
            
            row.innerHTML = `
                <td>${log.id}</td>
                <td>${log.owner_name}</td>
                <td>${log.datetime}</td>
                <td>
                    <button class="btn btn-link" data-bs-toggle="modal" data-bs-target="#messageModal" data-message="${log.message}">Раскрыть сообщение</button>
                </td>
                <td>${log.error_type}</td>
                <td>${log.color}</td>
            `;
            tableBody.appendChild(row);
        });
        const messageButtons = document.querySelectorAll('[data-bs-toggle="modal"]');
        messageButtons.forEach(button => {
            button.addEventListener('click', function() {
                const fullMessage = button.getAttribute('data-message');
                document.getElementById('fullMessageContent').textContent = fullMessage;
            });
        });

    } catch (error) {
        console.error("Ошибка загрузки логов:", error);
    }
}

setInterval(loadLogs, 600000, 1);

function toggleSort(column) {
    if (currentSort.column === column) {
        currentSort.order = currentSort.order === "asc" ? "desc" : "asc";
    } else {
        currentSort.column = column;
        currentSort.order = "asc";
    }
    saveFilters();
};

function resetFilters() {
    currentSort = { column: "datetime", order: "desc" };
    selectedDateRange = null;
    localStorage.removeItem("logFilters");
    document.getElementById("filter-id").value = "";
    document.getElementById("filter-owner").value = "";
    document.getElementById("filter-message").value = "";
    document.getElementById("filter-error-type").value = "";
    document.getElementById("start-date").value = "";
    document.getElementById("end-date").value = "";
    color = null;
    saveFilters();
}

// Добавление новой ошибки
async function addError() {
    const errorMessage = document.getElementById("errorMessage").value;
    const errorColor = document.getElementById("errorColor").value;
    const errorType = document.getElementById("errorType").value;

    if (!errorMessage || !errorColor || !errorType) {
        alert("Пожалуйста, заполните все поля.");
        return;
    }

    try {
        const response = await fetch("/logs/error", {
            method: "POST",
            credentials: 'include',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                error_message: errorMessage,
                color: errorColor,
                error_type: errorType,
            }),
        });

        if (response.ok) {
            console.log("Ошибка успешно добавлена!");
            applyErrorsToAllLogs()
        } else {
            const error = await response.json();
            alert(`Ошибка: ${error.detail}`);
        }
    } catch (err) {
        console.error("Ошибка при добавлении ошибки:", err);
        alert("Произошла ошибка при добавлении ошибки.");
    }
}

async function applyErrorsToAllLogs() {
    if (!confirm("Вы уверены, что хотите применить ошибки ко всем логам? Это действие изменит существующие записи.")) {
        return;
    }

    try {
        const response = await fetch("/logs/apply-errors-to-logs", {
            method: "POST",
        });

        if (response.ok) {
            alert("Ошибки успешно применены ко всем логам!");
            loadLogs();
        } else {
            const error = await response.json();
            alert(`Ошибка: ${error.detail}`);
        }
    } catch (err) {
        console.error("Ошибка при применении ошибок ко всем логам:", err);
        alert("Произошла ошибка при применении ошибок.");
    }
}


let selectedErrors = []; // Массив для хранения выбранных ошибок

async function showDeleteErrorModal() {
    const modal = new bootstrap.Modal(document.getElementById('deleteErrorModal'));
    const errorList = document.getElementById('errorList');
    errorList.innerHTML = ''; // Очистить предыдущий список

    try {
        // Получить список ошибок с сервера
        const response = await fetch('/logs/error-mapping', {
            credentials: 'include',
        });
        const errors = await response.json();

        if (response.ok) {
            // Добавить ошибки в список
            errors.forEach(error => {
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item d-flex align-items-center justify-content-between error-list-group-item';
                listItem.innerHTML = `
                    <span class="error-text">${error.message}</span>
                    <div class="form-check error-form-check ms-3">
                        <input type="checkbox" value="${error.id}" onchange="toggleSelectedError(${error.id}, this)" class="form-check-input error-form-check-input">
                    </div>
                `;
                errorList.appendChild(listItem);
            });

            modal.show();
        } else {
            alert(`Ошибка загрузки списка ошибок: ${errors.detail}`);
        }
    } catch (err) {
        console.error('Ошибка при загрузке списка ошибок:', err);
        alert('Произошла ошибка при загрузке списка ошибок.');
    }
}

// Функция для добавления/удаления ошибок в/из массива
function toggleSelectedError(errorId, checkbox) {
    if (checkbox.checked) {
        selectedErrors.push(errorId); // Добавить ошибку в массив
    } else {
        selectedErrors = selectedErrors.filter(id => id !== errorId); // Удалить ошибку из массива
    }
    console.log('Выбранные ошибки:', selectedErrors); // Для отладки
}

async function deleteSelectedErrors() {
    if (selectedErrors.length === 0) {
        alert('Выберите хотя бы одну ошибку для удаления.');
        return;
    }

    try {
        const response = await fetch('/logs/error/delete', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(selectedErrors),
        });

        if (response.ok) {
            alert('Выбранные ошибки успешно удалены!');
            selectedErrors = []; // Очистить массив
            showDeleteErrorModal(); // Перезагрузить список
        } else {
            const error = await response.json();
            alert(`Ошибка удаления: ${error.detail}`);
        }
    } catch (err) {
        console.error('Ошибка при удалении ошибок:', err);
        alert('Произошла ошибка при удалении ошибок.');
    }
}
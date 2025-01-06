document.addEventListener("DOMContentLoaded", function () {
    // Прослушиваем изменения в полях фильтров
    document.getElementById("filter-id").addEventListener("input", () => loadLogs());
    document.getElementById("filter-owner").addEventListener("input", () => loadLogs());
    document.getElementById("filter-message").addEventListener("input", () => loadLogs());

    // Добавить сюда другие события для других фильтров, если нужно
});

document.addEventListener("DOMContentLoaded", function () {
    const dateRangeButton = document.getElementById("date-range-selector");

    dateRangeButton.addEventListener("click", function () {
        const startDate = document.getElementById("start-date").value;
        const endDate = document.getElementById("end-date").value;

        if (startDate && endDate) {
            selectedDateRange = { from: startDate, to: endDate };
            loadLogs(); // Перезагружаем данные с новыми фильтрами
        } else {
            alert("Пожалуйста, выберите оба диапазона дат.");
        }
    });
});

function selectColor(selectedColor){
    color = selectedColor;
    loadLogs();
};

let currentSort = { column: "datetime", order: "desc" };
let selectedDateRange = null;
let color = null;
async function loadLogs(page = 1) {
    const pageSize = 50;

    const filters = {
        id: document.getElementById("filter-id").value.trim(),
        owner: document.getElementById("filter-owner").value.trim(),
        message: document.getElementById("filter-message").value.trim(),
        dateFrom: selectedDateRange?.from || null,
        dateTo: selectedDateRange?.to || null,
        errorType: document.getElementById("filter-error-type").value.trim(),
        color: color || null,
    };

    const sortColumn = currentSort.column || "datetime";
    const sortOrder = currentSort.order || "desc";

    // Формируем URL с параметрами
    const params = new URLSearchParams({
        page,
        page_size: pageSize,
        sort_by: sortColumn,
        sort_order: sortOrder
    });

    if (filters.id) params.append("log_id", filters.id);
    if (filters.owner) params.append("owner_name", filters.owner);
    if (filters.message) params.append("message", filters.message);
    if (filters.dateFrom) params.append("start_date", filters.dateFrom);
    if (filters.dateTo) params.append("end_date", filters.dateTo);
    if (filters.errorType) params.append("error_type", filters.errorType);
    if (filters.color) params.append("color", filters.color);

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

function toggleSort(column) {
    if (currentSort.column === column) {
        currentSort.order = currentSort.order === "asc" ? "desc" : "asc";
    } else {
        currentSort.column = column;
        currentSort.order = "asc";
    }
    loadLogs();
};

function resetFilters() {
    currentSort = { column: "datetime", order: "desc" };
    selectedDateRange = null;
    color = null;
    document.getElementById("filter-id").value = "";
    document.getElementById("filter-owner").value = "";
    document.getElementById("filter-message").value = "";
    document.getElementById("filter-error-type").value = "";
    loadLogs();
  }
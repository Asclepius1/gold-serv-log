async function loadReprts() {
    const response = await fetch('/files/reports', {
        method: 'GET',
        credentials: 'include',
    });

    if (response.ok) {
        const reports = await response.json();
        const tableBody = document.getElementById('reportTable');
        tableBody.innerHTML = '';

        reports.forEach(report => {

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${report.param}</td>
                <td>${report.name}</td>
                <td>
                    <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#staticBackdropReportAccessEdit" onclick="editReportAccess(${report.id})">
                        Изменить
                    </button>
                </td>
                <td>
                    <button type="button" class="btn btn-danger" id="deleteButtonReportId" onclick="deleteReport(${report.id})">
                        Удалить
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    } else {
        alert('Failed to load reports');
    }
}


async function addNewReport(){
    const param = document.getElementById('param').value;
    const name = document.getElementById('reportName').value;
    if (name && param){
        try {
            const response = await fetch('/files/reports', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    name: name,
                    param: param,
                })
            });

            if (response.ok) {
                loadReprts();
            } else {
                throw new Error('Ошибка регистраций отчета');
            }
        } catch (error) {
            console.error(error);
        }
    } else{
        console.log("Что-то пошло не так, попробуйте снова")
    }
}

async function deleteReport(reportId) {
    const response = await fetch(`/files/reports/${reportId}`, {
        method: 'DELETE',
        credentials: 'include'
    });
    if (response.ok) {
        loadReprts();
    } else {
        console.log(await response.text())
    }
}

async function editReportAccess(reportId) {
    const response = await fetch(`/owners/reports/${reportId}`, {
        method: 'GET',
        credentials: 'include',
    });
    document.getElementById("saveRepBtn").setAttribute("reportId", reportId)
    if (response.ok) {
        const owners = await response.json();
        const tableBody = document.getElementById('report-modal-tbody');
        tableBody.innerHTML = '';

        owners.forEach(owner => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${owner.id}</td>
                <td>${owner.name}</td>
                <td>
                    <input type="checkbox" class="form-check-input" id="access_${owner.id}" ${
                        owner.has_access === false ? '' : 'checked'
                    }>
                </td>
            `;
            tableBody.appendChild(row);
        });
    } else {
        alert('Не удалось загрузить владельцев');
    }
}

async function saveReportAccessChanges() {
    const reportId = document.getElementById("saveRepBtn").getAttribute("reportId");
    const checkboxes = document.querySelectorAll('[id^="access_"]');
    const accessChanges = Array.from(checkboxes).map(checkbox => ({
        owner_id: parseInt(checkbox.id.replace('access_', ''), 10),
        has_access: checkbox.checked,  // Состояние галочки
    }));

    try {
        const response = await fetch(`/files/reports/${reportId}/access`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(accessChanges),
        });

        if (response.ok) {
            alert('Доступы успешно обновлены');
            window.location.reload();
        } else {
            throw new Error('Ошибка обновления доступов');
        }
    } catch (error) {
        console.error(error);
        document.getElementById('modalBodyErrorText').hidden = false;
    }
}
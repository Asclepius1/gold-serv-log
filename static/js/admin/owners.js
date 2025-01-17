async function loadOwners() {
    const response = await fetch('/owners', {
        method: 'GET',
        credentials: 'include',
    });

    if (response.ok) {

        const owners = await response.json();
        const tableBody = document.getElementById('ownerTable');
        tableBody.innerHTML = '';

        owners.forEach(owner => {

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${owner.id}</td>
                <td><div class="input-group mb-3">
                    <input type="text" id="ownerName${owner.id}" class="form-control" placeholder="${owner.name}" aria-label="Text" aria-describedby="basic-addon1">
                </div></td>
                <td>
                    <button type="button" class="btn btn-primary" onclick="editOwner(${owner.id})">
                        Изменить
                    </button>
                </td>
                <td>
                    <button type="button" class="btn btn-danger" id="deleteButtonOwnerId" onclick="deleteOwner(${owner.id})">
                        Удалить
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    } else {
        alert('Failed to load users');
    }
}


async function editOwner(ownerId) {
    const deleteButton = document.getElementById("deleteButtonId")
    const name = document.getElementById(`ownerName${ownerId}`).value
    if(name){
        const ownerResponse = await fetch(`/owners/${ownerId}`, {
            method: 'PUT',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                name: name,})
        });
        if(ownerResponse.ok){
            document.getElementById("owner-tab").click()
        }
    }
}

function setNewOwner(value, id, elementId='dropdownOwner'){
    let isSuperUser = document.getElementById(elementId);
    isSuperUser.textContent = value;
    // document.getElementById('dropdownOwner').textContent = value;
    isSuperUser.setAttribute("owner-id", id);
}


async function deleteOwner(ownerId) {
    const response = await fetch(`/owners/${ownerId}`, {
        method: 'DELETE',
        credentials: 'include'
    });
    const worngElement = document.getElementById("wrongModal")
    if (response.ok) {
        document.getElementById("owner-tab").click()
    } else if (response.status == 500) {
        worngElement.hidden = false
        worngElement.textContent = "Что-то пошло не так, проверьте нету ли прикрепленных владельцев к пользователям"
        await new Promise(resolve => setTimeout(resolve, 5000));
        worngElement.hidden = true
    } else {
        worngElement.hidden = false
        worngElement.textContent = "Что-то пошло не так, попробуйте еше раз!"
        await new Promise(resolve => setTimeout(resolve, 5000));
        worngElement.hidden = true
    }
}

async function addNewOwner(){
    const name = document.getElementById('ownerNewName').value;
    if (name){
        try {
            const response = await fetch('/owners', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    name: name
                })
            });

            if (response.ok) {
                document.getElementById("closeBtnAddNewOwner").click()
                document.getElementById("owner-tab").click()
            } else {
                throw new Error('Ошибка регистраций');
            }
        } catch (error) {
            console.error(error);
            const errorMessage = document.getElementById('error-message');
            errorMessage.style.display = 'block';
            errorMessage.textContent = 'Что-то пошло не так, попробуйте обновить страницу и попробовать еще раз!';
        }
    } else{
        const errorMessage = document.getElementById('error-message');
        errorMessage.style.display = 'block';
        errorMessage.textContent = 'Некоторые поля остались пустыми, прошу заполнить и попробовать еще раз!';
    }
}

async function updateAllOwners(){
    const response = await fetch('/owners/update-all/', {
        method: 'GET',
        credentials: 'include',
    });

    if (response.ok){
        console.log(response.text())
        loadOwners()
        return
    }
    console.log(response.text())
}
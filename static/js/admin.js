async function loadUsers() {
    const response = await fetch('/users', {
        method: 'GET',
        credentials: 'include',
    });

    if (response.ok) {

        const ownerResponse = await fetch(`/owners`, {
            method: 'GET',
            credentials: 'include',
        });

        const owners = await ownerResponse.json();
        
        // загружаю так же в модальное окно "добавить пользователя" список владельцев
        const listItems = owners.map(owner => `<li><a class="dropdown-item" href="#" onclick="setNewOwner('${owner.name}', ${owner.id}, 'dropdownAddOwner') ">${owner.name}</a></li>`).join('');
        const dropdownMenuList = document.getElementById("dropdownMenuList");
        dropdownMenuList.innerHTML = listItems;
        // 

        const users = await response.json();
        const tableBody = document.getElementById('usersTable');
        tableBody.innerHTML = '';

        users.forEach(user => {
            const owner = owners.find(item => item.id === user.owners_id);
            const ownerName = owner ? owner.name : null;

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${user.id}</td>
                <td>${user.email}</td>
                <td>${user.name}</td>
                <td>${user.is_superuser ? 'Да' : 'Нет'}</td>
                <td>${ownerName}</td>
                <td>
                    <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#staticBackdropUserEdit" onclick="editUser(${user.id})">
                        Изменить
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    } else {
        alert('Failed to load users');
    }
}


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

async function loadLogs(page = 1) {
    const pageSize = 50; // Количество записей на странице
    try {
        const response = await fetch(`/logs?page=${page}&page_size=${pageSize}`, {
            method: 'GET',
            credentials: 'include',
        });
        const data = await response.json();

        // Очистка таблицы перед добавлением новых данных
        const tableBody = document.getElementById("logsTable");
        tableBody.innerHTML = "";

        // Заполнение таблицы данными
        data.data.forEach(log => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${log.id}</td>
                <td>${log.owner_name}</td>
                <td>${log.datetime}</td>
                <td>${log.message}</td>
                <td>ошибка</td>
                <td>red</td>
            `;
            tableBody.appendChild(row);
        });

        // // Добавьте обработку пагинации, если нужно
        // setupPagination(data.page, data.page_size, data.total);
    } catch (error) {
        console.error("Ошибка загрузки логов:", error);
    }
}

// Редактирование пользователя
async function editUser(userId) {
    const deleteButton = document.getElementById("deleteButtonUserId")
    deleteButton.hidden = false
    if(userId == 1){
        deleteButton.hidden = true
    }

    const ownerResponse = await fetch(`/owners`, {
        method: 'GET',
        credentials: 'include',
    });
    const owners = await ownerResponse.json();
    const listItems = owners.map(owner => `<li><a class="dropdown-item" href="#" onclick="setNewOwner('${owner.name}', ${owner.id})">${owner.name}</a></li>`).join('');
    
    const userResponse = await fetch(`/users/${userId}`, {
        method: 'GET',
        credentials: 'include',
    });
    
    
    
    if (userResponse.ok) {
        const user = await userResponse.json();
        const modalBody = document.getElementById("modal-tbody");
        const owner = owners.find(item => item.id === user.owners_id);
        const ownerName = owner ? owner.name : null;
        modalBody.innerHTML = `
        <tr>
            <td id='userId'>${user.id}</td>
            <td>
                <div class="input-group mb-3">
                    <input type="text" id="inputName" class="form-control" placeholder="${user.name}" aria-label="Text" aria-describedby="basic-addon1">
                </div>
            </th>
            <td>
                <div class="input-group mb-3 w-auto ">
                    <input type="text" id="inputEmail" class="form-control" placeholder="${user.email}" aria-label="Text" aria-describedby="basic-addon1">
                </div>
            </td>
            <td>
                <div class="dropdown">
                    <button class="btn btn-secondary dropdown-toggle w-auto" type="button" id="dropdownSuperuser" data-bs-toggle="dropdown" aria-expanded="false">
                    ${user.is_superuser ? 'Да' : 'Нет'}
                    </button>
                    <ul class="dropdown-menu" aria-labelledby="dropdownSuperuser">
                        <li><a class="dropdown-item" href="#" onclick="setSuperUser(true)">Да</a></li>
                        <li><a class="dropdown-item" href="#" onclick="setSuperUser(false)">Нет</a></li>
                    </ul>
                </div>
            </td>
            <td>
                <div class="dropdown">
                    <button class="btn btn-warning dropdown-toggle w-auto" type="button" id="dropdownOwner" owner-id="${user.owners_id}" data-bs-toggle="dropdown" aria-expanded="false">
                    ${ownerName}
                    </button>
                    <ul class="dropdown-menu" aria-labelledby="dropdownOwner">
                        ${listItems}
                    </ul>
                </div>
            </td>
            <td>
                <div class="input-group mb-3">
                    <input type="text" id="inputPassword" class="form-control" placeholder="Новый пароль" aria-label="Password" aria-describedby="basic-addon1">
                </div>
            </td>
        </tr>`;
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



function setSuperUser(value) {
    let isSuperUser = document.getElementById("dropdownSuperuser");
    isSuperUser.textContent = value;
    document.getElementById('dropdownSuperuser').textContent = value ? 'Да' : 'Нет';
}


function setNewOwner(value, id, elementId='dropdownOwner'){
    let isSuperUser = document.getElementById(elementId);
    isSuperUser.textContent = value;
    // document.getElementById('dropdownOwner').textContent = value;
    isSuperUser.setAttribute("owner-id", id);
}

async function SaveUserChanges(){

    const userId = document.getElementById('userId').textContent.replace(/\s/g, '');

    const inputName = document.getElementById('inputName');
    const inputEmail = document.getElementById('inputEmail');
    const inputPassword = document.getElementById('inputPassword');
    const inputOwner = document.getElementById('inputOwner');

    const nameInputValue = inputName.value;
    const emailInputValue = inputEmail.value;
    const passwordInputValue = inputPassword.value;

    const is_superuser_bool = document.getElementById("dropdownSuperuser").textContent;
    const is_superuser = is_superuser_bool == "Да" ? true : false 
    
    const ownerId = document.getElementById("dropdownOwner").getAttribute("owner-id");

    console.log(ownerId)


    const data = {};
    if (passwordInputValue) data.password = passwordInputValue;
    if (emailInputValue) data.email = emailInputValue;
    if (is_superuser !== undefined) data.is_superuser = is_superuser;
    data.owners_id = ownerId;
    nameInputValue ? data.name = nameInputValue : data.name = inputName.getAttribute("placeholder")

    const response = await fetch(`/users/${userId}`, {
        method: 'PATCH',
        credentials: 'include', // Для CookieTransport
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(
            data,
        ),
    });
    if (response.ok) {
        window.location.reload();
        // loadUsers();
    } else {
        const modalBody = document.getElementById("modalBodyErrorText") 
        modalBody.hidden = false
    }
}

async function DeleteUser() {
    const userId = document.getElementById('userId').textContent.replace(/\s/g, '');

    const response = await fetch(`/users/${userId}`, {
        method: 'DELETE',
        credentials: 'include'
    });
    if (response.ok) {
        window.location.reload();
        // loadUsers();
    } else {
        const modalBody = document.getElementById("modalBodyErrorText") 
        modalBody.hidden = false
    }

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

async function addNewUser(){
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const owner = document.getElementById('dropdownAddOwner').getAttribute("owner-id");
    if (name && email && password){
        try {
            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    email: email,
                    name: name,
                    owners_id: owner,
                    password: password, })
            });

            if (response.ok) {
                window.location.reload();
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


// Загрузка пользователей при загрузке страницы
window.onload = loadUsers;
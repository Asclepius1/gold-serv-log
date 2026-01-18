async function loadUsers() {
  const response = await fetch("/users", {
    method: "GET",
    credentials: "include",
  });

  if (response.ok) {
    const ownerResponse = await fetch(`/owners`, {
      method: "GET",
      credentials: "include",
    });

    const owners = await ownerResponse.json();

    // загружаю так же в модальное окно "добавить пользователя" список владельцев
    const listItems = owners
      .map(
        (owner) =>
          `<li><a class="dropdown-item" href="#" onclick="setNewOwner('${owner.name}', ${owner.id}, 'dropdownAddOwner') ">${owner.name}</a></li>`
      )
      .join("");
    const dropdownMenuList = document.getElementById("dropdownMenuList");
    dropdownMenuList.innerHTML = listItems;
    //

    const users = await response.json();
    const tableBody = document.getElementById("usersTable");
    tableBody.innerHTML = "";

    users.forEach((user) => {
      const owner = owners.find((item) => item.id === user.owners_id);
      const ownerName = owner ? owner.name : null;

      // Определяем роль пользователя
      let role = "Пользователь";
      if (user.is_superuser) {
        role = "Администратор";
      } else if (user.is_hr) {
        role = "HR";
      }

      const row = document.createElement("tr");
      row.innerHTML = `
                <td>${user.id}</td>
                <td>${user.email}</td>
                <td>${user.name}</td>
                <td>${role}</td>
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
    showToast("Failed to load users", "error");
  }
}

async function editUser(userId) {
  const deleteButton = document.getElementById("deleteButtonUserId");
  deleteButton.hidden = false;
  if (userId == 1) {
    deleteButton.hidden = true;
  }

  const ownerResponse = await fetch(`/owners`, {
    method: "GET",
    credentials: "include",
  });
  const owners = await ownerResponse.json();
  const listItems = owners
    .map(
      (owner) =>
        `<li><a class="dropdown-item" href="#" onclick="setNewOwner('${owner.name}', ${owner.id})">${owner.name}</a></li>`
    )
    .join("");

  const userResponse = await fetch(`/users/${userId}`, {
    method: "GET",
    credentials: "include",
  });

  if (userResponse.ok) {
    const user = await userResponse.json();
    const modalBody = document.getElementById("modal-tbody");
    const owner = owners.find((item) => item.id === user.owners_id);
    const ownerName = owner ? owner.name : null;
    modalBody.innerHTML = `
        <tr>
            <td id='userId'>${user.id}</td>
            <td>
                <div class="input-group mb-3">
                    <input type="text" id="inputName" class="form-control" placeholder="${
                      user.name
                    }" aria-label="Text" aria-describedby="basic-addon1">
                </div>
            </th>
            <td>
                <div class="input-group mb-3 w-auto ">
                    <input type="text" id="inputEmail" class="form-control" placeholder="${
                      user.email
                    }" aria-label="Text" aria-describedby="basic-addon1">
                </div>
            </td>
            <td>
                <div class="dropdown">
                    <button class="btn btn-secondary dropdown-toggle w-auto" type="button" id="dropdownSuperuser" data-bs-toggle="dropdown" aria-expanded="false">
                    ${user.is_superuser ? "Да" : "Нет"}
                    </button>
                    <ul class="dropdown-menu" aria-labelledby="dropdownSuperuser">
                        <li><a class="dropdown-item" href="#" onclick="setSuperUser(true)">Да</a></li>
                        <li><a class="dropdown-item" href="#" onclick="setSuperUser(false)">Нет</a></li>
                    </ul>
                </div>
            </td>
            <td>
                <div class="dropdown">
                    <button class="btn btn-warning dropdown-toggle w-auto" type="button" id="dropdownOwner" owner-id="${
                      user.owners_id
                    }" data-bs-toggle="dropdown" aria-expanded="false">
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

function setSuperUser(value) {
  let isSuperUser = document.getElementById("dropdownSuperuser");
  isSuperUser.textContent = value;
  document.getElementById("dropdownSuperuser").textContent = value
    ? "Да"
    : "Нет";
}

async function SaveUserChanges() {
  const userId = document
    .getElementById("userId")
    .textContent.replace(/\s/g, "");

  const inputName = document.getElementById("inputName");
  const inputEmail = document.getElementById("inputEmail");
  const inputPassword = document.getElementById("inputPassword");
  const inputOwner = document.getElementById("inputOwner");

  const nameInputValue = inputName.value;
  const emailInputValue = inputEmail.value;
  const passwordInputValue = inputPassword.value;

  const is_superuser_bool = document
    .getElementById("dropdownSuperuser")
    .textContent.replace(/\s/g, "");
  const is_superuser = is_superuser_bool == "Да" ? true : false;

  const ownerId = document
    .getElementById("dropdownOwner")
    .getAttribute("owner-id");

  const data = {};
  if (passwordInputValue) data.password = passwordInputValue;
  if (emailInputValue) data.email = emailInputValue;
  if (is_superuser !== undefined) data.is_superuser = is_superuser;
  data.owners_id = ownerId;
  nameInputValue
    ? (data.name = nameInputValue)
    : (data.name = inputName.getAttribute("placeholder"));
  const response = await fetch(`/users/${userId}`, {
    method: "PATCH",
    credentials: "include", // Для CookieTransport
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (response.ok) {
    window.location.reload();
    // loadUsers();
  } else {
    const modalBody = document.getElementById("modalBodyErrorText");
    modalBody.hidden = false;
  }
}

async function DeleteUser() {
  const userId = document
    .getElementById("userId")
    .textContent.replace(/\s/g, "");

  const response = await fetch(`/users/${userId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (response.ok) {
    window.location.reload();
    // loadUsers();
  } else {
    const modalBody = document.getElementById("modalBodyErrorText");
    modalBody.hidden = false;
  }
}

async function addNewUser() {
  const name = document.getElementById("name").value;
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const role = document.getElementById("role").value || "user";
  const owner = document
    .getElementById("dropdownAddOwner")
    .getAttribute("owner-id");

  // Валидация: владелец обязателен только для обычных пользователей
  if (role === "user" && !owner) {
    const errorMessage = document.getElementById("error-message");
    errorMessage.style.display = "block";
    errorMessage.textContent = "Владелец обязателен для обычных пользователей!";
    return;
  }

  if (name && email && password) {
    try {
      const isAdmin = role === "admin";
      const isHr = role === "hr";

      const response = await fetch("/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email,
          name: name,
          owners_id: owner || null,
          password: password,
          is_superuser: isAdmin,
          is_hr: isHr,
        }),
      });

      if (response.ok) {
        // Очищаем форму
        document.getElementById("name").value = "";
        document.getElementById("email").value = "";
        document.getElementById("password").value = "";
        document.getElementById("role").value = "user";
        document
          .getElementById("dropdownAddOwner")
          .setAttribute("owner-id", "");
        document.getElementById("error-message").style.display = "none";

        window.location.reload();
      } else {
        throw new Error("Ошибка регистраций");
      }
    } catch (error) {
      console.error(error);
      const errorMessage = document.getElementById("error-message");
      errorMessage.style.display = "block";
      errorMessage.textContent =
        "Что-то пошло не так, попробуйте обновить страницу и попробовать еще раз!";
    }
  } else {
    const errorMessage = document.getElementById("error-message");
    errorMessage.style.display = "block";
    errorMessage.textContent =
      "Некоторые поля остались пустыми, прошу заполнить и попробовать еще раз!";
  }
}

// Функция для переключения видимости поля владельца
function toggleOwnerField() {
  const role = document.getElementById("role").value;
  const ownerContainer = document.getElementById("ownerContainer");
  const dropdownAddOwner = document.getElementById("dropdownAddOwner");

  if (role === "user") {
    // Для обычных пользователей показываем владельца и отмечаем как обязательный
    ownerContainer.style.display = "block";
  } else {
    // Для админа и HR скрываем владельца
    ownerContainer.style.display = "none";
    dropdownAddOwner.setAttribute("owner-id", "");
  }
}

window.onload = loadUsers;

document.getElementById('login-form').addEventListener('submit', async function (event) {
    event.preventDefault(); // Отменить стандартное поведение формы

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    // const rememberMe = document.getElementById('remember').checked;

    try {
        const response = await fetch('/auth/jwt/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                // 'Accept': 'application/json',
            },
            // body: JSON.stringify({ username: username, password: password })
            body: new URLSearchParams({
                username: username,  // использует 'username' вместо 'email' в запросе
                password: password
            }),
            credentials: 'include'
        });

        if (response.ok) {
            window.location.href = '/internal';
        } else {
            throw new Error('Ошибка авторизации');
        }
    } catch (error) {
        console.error(error);
        const errorMessage = document.getElementById('error-message');
        errorMessage.style.display = 'block';
        errorMessage.textContent = 'Неверный email или пароль.';
    }
});
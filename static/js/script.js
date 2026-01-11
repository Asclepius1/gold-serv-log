function sayHello() {
  if (window.showToast)
    showToast("Привет! Это ваше веб-приложение на FastAPI.", "info");
  else alert("Привет! Это ваше веб-приложение на FastAPI.");
}

document.getElementById("login-btn").addEventListener("click", () => {
  window.location.href = "login";
});

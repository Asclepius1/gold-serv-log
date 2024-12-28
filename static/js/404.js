var $copyContainer = $(".copy-container p");
var text = $copyContainer.text();
var chars = text.split("");

// Очистка контейнера и добавление разбитого текста
$copyContainer.html("");
chars.forEach(function(char) {
    $copyContainer.append(`<span class="char">${char}</span>`);
});

// Анимация с GSAP
var splitTextTimeline = gsap.timeline();
splitTextTimeline.fromTo(".char", { opacity: 0, y: -20 }, { opacity: 1, y: 0, stagger: 0.05 });

"use strict";

document.querySelectorAll(".trend-card").forEach(function (card) {
    const markers = Array.from(card.querySelectorAll(".trend-game"));
    const detail = card.querySelector(".trend-detail");
    const hint = card.querySelector(".trend-interaction");
    if (!markers.length || !detail || !hint) return;

    hint.hidden = false;

    function showGame(marker) {
        markers.forEach(function (item) {
            item.classList.toggle("is-active", item === marker);
        });
        detail.textContent = marker.dataset.detail;
    }

    markers.forEach(function (marker, index) {
        marker.addEventListener("mouseenter", function () { showGame(marker); });
        marker.addEventListener("focus", function () { showGame(marker); });
        marker.addEventListener("click", function (event) {
            // Without this enhancement, each marker links to the game table.
            event.preventDefault();
            showGame(marker);
        });
        marker.addEventListener("keydown", function (event) {
            let next;
            if (event.key === "ArrowLeft") next = Math.max(0, index - 1);
            if (event.key === "ArrowRight") next = Math.min(markers.length - 1, index + 1);
            if (event.key === "Home") next = 0;
            if (event.key === "End") next = markers.length - 1;
            if (next !== undefined) {
                event.preventDefault();
                markers[next].focus();
            }
        });
    });
});

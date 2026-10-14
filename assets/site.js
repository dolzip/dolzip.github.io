"use strict";
document.addEventListener("keydown", event => {
  if (event.key !== "Escape") return;
  const menu = document.querySelector(".languages[open]");
  if (menu) { menu.open = false; menu.querySelector("summary").focus(); }
});

"use strict";

const number = new URLSearchParams(window.location.search).get("number");
const numberElement = document.querySelector("#order-number");
numberElement.textContent = number || "查無訂單編號";
if (!number) numberElement.classList.add("thankyou-number--missing");

const memberButton = document.querySelector(".navigation__member");
memberButton?.addEventListener("click", (event) => {
  if (!localStorage.getItem("token")) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  localStorage.removeItem("token");
  window.location.replace("/");
}, { capture: true });

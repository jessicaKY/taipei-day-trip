"use strict";

window.addEventListener("auth:ready", (event) => {
  const user = event.detail;
  const name = document.querySelector("#booking-user-name");
  const empty = document.querySelector("#booking-empty");
  if (user) {
    name.textContent = user.name;
    empty.textContent = "目前沒有任何待預訂的行程";
  } else {
    name.textContent = "旅客";
    empty.textContent = "目前沒有任何待預訂的行程";
  }
});

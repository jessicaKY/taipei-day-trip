"use strict";

const number = new URLSearchParams(window.location.search).get("number");
const numberElement = document.querySelector("#order-number");
numberElement.textContent = number || "查無訂單編號";
if (!number) numberElement.classList.add("thankyou-number--missing");

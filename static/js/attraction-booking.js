"use strict";

document.querySelector("#booking-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  const user = window.currentUser !== undefined ? window.currentUser : await window.auth.checkAuthStatus();
  if (!user) {
    window.auth.openAuthDialog("signin");
    return;
  }
  const values = new FormData(form);
  const time = values.get("time");
  const attractionId = Number(window.location.pathname.split("/").filter(Boolean).at(-1));
  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  try {
    const response = await fetch("/api/booking", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...window.auth.authHeaders() },
      body: JSON.stringify({ attractionId, date: values.get("date"), time, price: time === "afternoon" ? 2500 : 2000 }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || "建立預訂失敗");
    window.location.href = "/booking";
  } catch (error) {
    console.error(error);
    alert(error.message);
    submitButton.disabled = false;
  }
});

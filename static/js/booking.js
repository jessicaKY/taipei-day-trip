"use strict";

const bookingElements = {
  address: document.querySelector("#booking-address"),
  content: document.querySelector("#booking-content"),
  date: document.querySelector("#booking-date"),
  deleteButton: document.querySelector("#delete-booking"),
  email: document.querySelector("#contact-email"),
  empty: document.querySelector("#booking-empty"),
  image: document.querySelector("#booking-image"),
  name: document.querySelector("#booking-attraction-name"),
  price: document.querySelector("#booking-price"),
  time: document.querySelector("#booking-time"),
  total: document.querySelector("#booking-total"),
  userName: document.querySelector("#booking-user-name"),
  contactName: document.querySelector("#contact-name"),
};

let bookingInitialized = false;

function showEmptyBooking() {
  bookingElements.content.hidden = true;
  bookingElements.empty.hidden = false;
  document.body.classList.add("booking-is-empty");
}

function renderBooking(booking) {
  bookingElements.image.src = booking.attraction.image;
  bookingElements.image.alt = booking.attraction.name;
  bookingElements.name.textContent = booking.attraction.name;
  bookingElements.date.textContent = booking.date;
  bookingElements.time.textContent = booking.time === "morning" ? "早上 9 點到下午 4 點" : "下午 2 點到晚上 9 點";
  bookingElements.price.textContent = booking.price;
  bookingElements.total.textContent = booking.price;
  bookingElements.address.textContent = booking.attraction.address;
  bookingElements.empty.hidden = true;
  bookingElements.content.hidden = false;
  document.body.classList.remove("booking-is-empty");
}

async function initializeBooking(user) {
  if (bookingInitialized) return;
  bookingInitialized = true;
  if (!user) {
    window.location.replace("/");
    return;
  }
  bookingElements.userName.textContent = user.name;
  bookingElements.contactName.value = user.name;
  bookingElements.email.value = user.email;
  try {
    const response = await fetch("/api/booking", { headers: { Accept: "application/json", ...window.auth.authHeaders() } });
    if (response.status === 403) {
      localStorage.removeItem("token");
      window.location.replace("/");
      return;
    }
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || "預訂資料載入失敗");
    if (payload.data) renderBooking(payload.data);
    else showEmptyBooking();
  } catch (error) {
    console.error(error);
    showEmptyBooking();
  }
}

bookingElements.deleteButton.addEventListener("click", async () => {
  bookingElements.deleteButton.disabled = true;
  try {
    const response = await fetch("/api/booking", { method: "DELETE", headers: window.auth.authHeaders() });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || "刪除預訂失敗");
    window.location.reload();
  } catch (error) {
    console.error(error);
    bookingElements.deleteButton.disabled = false;
  }
});

window.addEventListener("auth:ready", (event) => initializeBooking(event.detail));
if (window.currentUser !== undefined) initializeBooking(window.currentUser);

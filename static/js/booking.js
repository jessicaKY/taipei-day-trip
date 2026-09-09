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
  contactPhone: document.querySelector("#contact-phone"),
  confirmButton: document.querySelector("#confirm-order"),
  paymentMessage: document.querySelector("#payment-message"),
};

let bookingInitialized = false;
let currentBooking = null;
let tappayReady = false;

function setupTapPay() {
  if (!window.TPDirect || tappayReady) return;
  TPDirect.setupSDK(171043, "app_eIdsbpSdPs07WIlnrKvVJ8XyxvsXFqTvG5XhYdy5vVGjAho4tzRcQ9px2xDQ", "sandbox");
  TPDirect.card.setup({
    fields: {
      number: { element: "#card-number", placeholder: "**** **** **** ****" },
      expirationDate: { element: "#card-expiration-date", placeholder: "MM / YY" },
      ccv: { element: "#card-ccv", placeholder: "CVV" },
    },
    styles: {
      input: { color: "#757575", "font-size": "16px", "font-family": "Noto Sans TC, Arial, sans-serif" },
      ":focus": { color: "#666666" },
      ".valid": { color: "green" },
      ".invalid": { color: "#d33" },
    },
    // The assignment reference keeps the complete sandbox card number visible.
    isMaskCreditCardNumber: false,
  });
  TPDirect.card.onUpdate((status) => {
    document.querySelectorAll(".tpfield").forEach((field) => field.classList.toggle("is-valid", status.canGetPrime));
  });
  tappayReady = true;
}

function showEmptyBooking() {
  bookingElements.content.hidden = true;
  bookingElements.empty.hidden = false;
  document.body.classList.add("booking-is-empty");
}

function renderBooking(booking) {
  currentBooking = booking;
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

bookingElements.confirmButton.addEventListener("click", () => {
  const contact = {
    name: bookingElements.contactName.value.trim(),
    email: bookingElements.email.value.trim(),
    phone: bookingElements.contactPhone.value.trim(),
  };
  bookingElements.paymentMessage.textContent = "";
  if (!contact.name || !contact.email || !contact.phone) {
    bookingElements.paymentMessage.textContent = "請完整填寫聯絡資訊";
    return;
  }
  setupTapPay();
  if (!tappayReady || !TPDirect.card.getTappayFieldsStatus().canGetPrime) {
    bookingElements.paymentMessage.textContent = "信用卡資訊不正確，請重新確認";
    return;
  }
  bookingElements.confirmButton.disabled = true;
  bookingElements.confirmButton.textContent = "付款處理中…";
  TPDirect.card.getPrime(async (result) => {
    try {
      if (result.status !== 0) throw new Error(result.msg || "無法取得付款憑證");
      const response = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...window.auth.authHeaders() },
        body: JSON.stringify({ prime: result.card.prime, order: { price: currentBooking.price, trip: currentBooking, contact } }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "付款失敗");
      if (payload.data.payment.status !== 0) throw new Error(payload.data.payment.message || "付款失敗");
      window.location.href = `/thankyou?number=${encodeURIComponent(payload.data.number)}`;
    } catch (error) {
      bookingElements.paymentMessage.textContent = error.message;
      bookingElements.confirmButton.disabled = false;
      bookingElements.confirmButton.textContent = "確認訂購並付款";
    }
  });
});

window.addEventListener("load", setupTapPay);

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

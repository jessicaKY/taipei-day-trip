"use strict";

const elements = {
  address: document.querySelector("#attraction-address"),
  bookingForm: document.querySelector("#booking-form"),
  description: document.querySelector("#attraction-description"),
  image: document.querySelector("#attraction-image"),
  indicators: document.querySelector("#image-indicators"),
  name: document.querySelector("#attraction-name"),
  nextImage: document.querySelector("#next-image"),
  previousImage: document.querySelector("#previous-image"),
  price: document.querySelector("#tour-price"),
  status: document.querySelector("#page-status"),
  summary: document.querySelector("#attraction-summary"),
  tourDate: document.querySelector("#tour-date"),
  transport: document.querySelector("#attraction-transport"),
};

const state = { attraction: null, currentImage: 0 };

function getAttractionId() {
  const id = Number(window.location.pathname.split("/").filter(Boolean).at(-1));
  return Number.isInteger(id) && id > 0 ? id : null;
}

function setStatus(message = "") {
  elements.status.textContent = message;
}

function renderIndicators() {
  const fragment = document.createDocumentFragment();
  state.attraction.images.forEach((_, index) => {
    const indicator = document.createElement("span");
    indicator.className = "slideshow__indicator";
    indicator.classList.toggle("slideshow__indicator--active", index === state.currentImage);
    fragment.append(indicator);
  });
  elements.indicators.replaceChildren(fragment);
}

function renderCurrentImage() {
  const images = state.attraction.images;
  elements.image.src = images[state.currentImage] || "";
  elements.image.alt = `${state.attraction.name}，第 ${state.currentImage + 1} 張景點圖片`;
  renderIndicators();

  const hasMultipleImages = images.length > 1;
  elements.previousImage.hidden = !hasMultipleImages;
  elements.nextImage.hidden = !hasMultipleImages;
}

function changeImage(step) {
  const total = state.attraction?.images.length || 0;
  if (total < 2) return;
  state.currentImage = (state.currentImage + step + total) % total;
  renderCurrentImage();
}

function renderAttraction(attraction) {
  state.attraction = attraction;
  document.title = `${attraction.name}｜台北一日遊`;
  elements.name.textContent = attraction.name;
  elements.summary.textContent = `${attraction.category} at ${attraction.mrt || "無鄰近捷運站"}`;
  elements.description.textContent = attraction.description;
  elements.address.textContent = attraction.address;
  elements.transport.textContent = attraction.transport;
  renderCurrentImage();
}

async function loadAttraction() {
  const attractionId = getAttractionId();
  if (!attractionId) {
    setStatus("景點編號不正確");
    return;
  }

  try {
    const response = await fetch(`/api/attraction/${attractionId}`, {
      headers: { Accept: "application/json" },
    });
    const payload = await response.json();
    if (!response.ok || payload.error || !payload.data) {
      throw new Error(payload.message || "景點資料載入失敗");
    }
    renderAttraction(payload.data);
    setStatus("");
  } catch (error) {
    elements.name.textContent = "無法載入景點";
    setStatus("景點資料暫時無法載入，請稍後再試");
    console.error(error);
  }
}

function updatePrice(time) {
  elements.price.textContent = time === "afternoon" ? "新台幣 2500 元" : "新台幣 2000 元";
}

function setMinimumDate() {
  const today = new Date();
  const localToday = new Date(today.getTime() - today.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 10);
  elements.tourDate.min = localToday;
}

elements.previousImage.addEventListener("click", () => changeImage(-1));
elements.nextImage.addEventListener("click", () => changeImage(1));

elements.bookingForm.addEventListener("change", (event) => {
  if (event.target.matches('input[name="time"]')) updatePrice(event.target.value);
});

elements.bookingForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!elements.bookingForm.reportValidity()) return;
});

setMinimumDate();
loadAttraction();

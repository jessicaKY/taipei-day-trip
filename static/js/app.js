"use strict";

const API = {
  attractions: "/api/attractions",
  categories: "/api/categories",
  mrts: "/api/mrts",
};

const state = {
  category: "",
  keyword: "",
  nextPage: 0,
  isLoading: false,
  requestId: 0,
  controller: null,
};

const elements = {
  attractions: document.querySelector("#attractions"),
  categoryButton: document.querySelector("#category-button"),
  categoryMenu: document.querySelector("#category-menu"),
  currentCategory: document.querySelector("#current-category"),
  keyword: document.querySelector("#keyword"),
  mrtLeft: document.querySelector("#mrt-left"),
  mrtList: document.querySelector("#mrt-list"),
  mrtRight: document.querySelector("#mrt-right"),
  searchForm: document.querySelector("#search-form"),
  sentinel: document.querySelector("#load-sentinel"),
  status: document.querySelector("#status"),
};

function setStatus(message = "") {
  elements.status.textContent = message;
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  const payload = await response.json();
  if (payload.error) {
    throw new Error(payload.message || "API 回傳錯誤");
  }
  return payload;
}

function createAttractionCard(attraction) {
  const link = document.createElement("a");
  link.className = "attraction-card";
  link.href = `/attraction/${encodeURIComponent(attraction.id)}`;
  link.setAttribute("aria-label", `查看景點：${attraction.name}`);

  const picture = document.createElement("div");
  picture.className = "attraction-card__picture";

  const image = document.createElement("img");
  image.src = attraction.images?.[0] || "";
  image.alt = attraction.name || "台北景點";
  image.loading = "lazy";
  image.decoding = "async";

  const name = document.createElement("h2");
  name.className = "attraction-card__name";
  name.textContent = attraction.name || "未命名景點";

  const details = document.createElement("div");
  details.className = "attraction-card__details";

  const mrt = document.createElement("span");
  mrt.textContent = attraction.mrt || "無鄰近捷運站";

  const category = document.createElement("span");
  category.textContent = attraction.category || "未分類";

  picture.append(image, name);
  details.append(mrt, category);
  link.append(picture, details);
  return link;
}

function renderAttractions(attractions, { replace = false } = {}) {
  if (replace) elements.attractions.replaceChildren();
  const fragment = document.createDocumentFragment();
  attractions.forEach((attraction) => fragment.append(createAttractionCard(attraction)));
  elements.attractions.append(fragment);
}

function buildAttractionsUrl(page) {
  const params = new URLSearchParams({ page: String(page) });
  if (state.category) params.set("category", state.category);
  if (state.keyword) params.set("keyword", state.keyword);
  return `${API.attractions}?${params.toString()}`;
}

async function loadAttractions({ page = 0, replace = false } = {}) {
  if (state.isLoading && !replace) return;
  if (replace && state.controller) state.controller.abort();

  const thisRequest = ++state.requestId;
  const controller = new AbortController();
  state.controller = controller;
  state.isLoading = true;
  setStatus("景點載入中…");

  try {
    const response = await fetch(buildAttractionsUrl(page), {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`API request failed: ${response.status}`);
    const payload = await response.json();
    if (payload.error) throw new Error(payload.message || "API 回傳錯誤");
    if (thisRequest !== state.requestId) return;

    const attractions = Array.isArray(payload.data) ? payload.data : [];
    renderAttractions(attractions, { replace });
    state.nextPage = payload.nextPage;

    if (replace && attractions.length === 0) {
      setStatus("找不到符合條件的景點");
    } else {
      setStatus("");
    }
  } catch (error) {
    if (error.name === "AbortError") return;
    if (thisRequest === state.requestId) {
      if (replace) elements.attractions.replaceChildren();
      state.nextPage = null;
      setStatus("景點資料暫時無法載入，請稍後再試");
      console.error(error);
    }
  } finally {
    if (thisRequest === state.requestId) {
      state.isLoading = false;
      state.controller = null;
    }
  }
}

function openCategoryMenu() {
  elements.categoryMenu.hidden = false;
  elements.categoryButton.setAttribute("aria-expanded", "true");
}

function closeCategoryMenu() {
  elements.categoryMenu.hidden = true;
  elements.categoryButton.setAttribute("aria-expanded", "false");
}

function formatCategoryLabel(category) {
  return category ? category.replace(/\u3000/g, "") : "全部分類";
}

function selectCategory(category) {
  state.category = category;
  elements.currentCategory.textContent = formatCategoryLabel(category);
  closeCategoryMenu();
}

function renderCategories(categories) {
  const fragment = document.createDocumentFragment();
  const allCategories = ["", ...categories];

  allCategories.forEach((category) => {
    const button = document.createElement("button");
    button.className = "category__option";
    button.type = "button";
    button.role = "option";
    button.textContent = formatCategoryLabel(category);
    button.addEventListener("click", () => selectCategory(category));
    fragment.append(button);
  });

  elements.categoryMenu.replaceChildren(fragment);
}

async function loadCategories() {
  try {
    const payload = await fetchJson(API.categories);
    renderCategories(Array.isArray(payload.data) ? payload.data : []);
  } catch (error) {
    renderCategories([]);
    console.error(error);
  }
}

function renderMrts(mrts) {
  const fragment = document.createDocumentFragment();
  mrts.forEach((mrtName) => {
    const button = document.createElement("button");
    button.className = "mrt-bar__station";
    button.type = "button";
    button.textContent = mrtName;
    button.addEventListener("click", () => {
      elements.keyword.value = mrtName;
      state.keyword = mrtName;
      loadAttractions({ page: 0, replace: true });
    });
    fragment.append(button);
  });
  elements.mrtList.replaceChildren(fragment);
}

async function loadMrts() {
  try {
    const payload = await fetchJson(API.mrts);
    renderMrts(Array.isArray(payload.data) ? payload.data : []);
  } catch (error) {
    console.error(error);
  }
}

elements.categoryButton.addEventListener("click", () => {
  if (elements.categoryMenu.hidden) openCategoryMenu();
  else closeCategoryMenu();
});

elements.searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.keyword = elements.keyword.value.trim();
  closeCategoryMenu();
  loadAttractions({ page: 0, replace: true });
});

elements.mrtLeft.addEventListener("click", () => {
  elements.mrtList.scrollBy({ left: -300, behavior: "smooth" });
});

elements.mrtRight.addEventListener("click", () => {
  elements.mrtList.scrollBy({ left: 300, behavior: "smooth" });
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".category")) closeCategoryMenu();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeCategoryMenu();
});

const observer = new IntersectionObserver(
  (entries) => {
    if (entries[0].isIntersecting && state.nextPage !== null && !state.isLoading) {
      loadAttractions({ page: state.nextPage });
    }
  },
  { rootMargin: "0px" },
);

async function initialize() {
  await Promise.allSettled([
    loadCategories(),
    loadMrts(),
    loadAttractions({ page: 0, replace: true }),
  ]);
  observer.observe(elements.sentinel);
}

initialize();

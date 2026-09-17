"use strict";

const memberName = document.querySelector("#member-name");
const hostUrl = document.querySelector("#mcp-host-url");
const tokenOutput = document.querySelector("#mcp-token");
const tokenButton = document.querySelector("#generate-token");
const logoutButton = document.querySelector("#member-logout");
const message = document.querySelector("#member-message");
const ordersList = document.querySelector("#member-orders-list");
const ordersStatus = document.querySelector("#member-orders-status");
const deleteDialog = document.querySelector("#member-delete-dialog");
const deleteOrderText = document.querySelector("#member-delete-order");
const deleteMessage = document.querySelector("#member-delete-message");
const deleteCancel = document.querySelector("#member-delete-cancel");
const deleteConfirm = document.querySelector("#member-delete-confirm");
const MCP_TOKEN_SESSION_KEY = "taipeiDayTripMcpToken";
let orderPendingDeletion = null;
let signedInMember = null;

async function requireMember() {
  const user = window.currentUser !== undefined
    ? window.currentUser
    : await window.auth.checkAuthStatus();
  if (!user) {
    window.location.replace("/");
    return null;
  }
  memberName.textContent = user.name;
  signedInMember = user;
  return user;
}

function cachedMcpTokenFor(userId) {
  try {
    const cached = JSON.parse(sessionStorage.getItem(MCP_TOKEN_SESSION_KEY));
    return cached?.userId === userId ? cached.token : null;
  } catch (error) {
    sessionStorage.removeItem(MCP_TOKEN_SESSION_KEY);
    return null;
  }
}

async function loadMcpConfig(user) {
  try {
    const response = await fetch("/api/member/mcp-config", {
      headers: { Accept: "application/json", ...window.auth.authHeaders() },
    });
    const payload = await response.json();
    if (!response.ok || !payload.data) throw new Error();
    hostUrl.textContent = payload.data.hostUrl;
    const cachedToken = cachedMcpTokenFor(user.id);
    if (cachedToken) tokenOutput.textContent = cachedToken;
    else if (payload.data.hasToken) tokenOutput.textContent = "已產生（基於安全性不再次顯示，若遺失請更新金鑰）";
    else tokenOutput.textContent = "尚未產生";
  } catch (error) {
    hostUrl.textContent = "無法取得 MCP Host URL";
  }
}

function renderOrders(orders) {
  ordersList.replaceChildren();
  if (!orders.length) {
    ordersStatus.textContent = "目前沒有已完成的行程";
    return;
  }
  ordersStatus.textContent = "";
  orders.forEach((order) => {
    const card = document.createElement("article");
    card.className = "member-order";

    const image = document.createElement("img");
    image.className = "member-order__image";
    image.src = order.trip.attraction.image;
    image.alt = order.trip.attraction.name;

    const deleteButton = document.createElement("button");
    deleteButton.className = "member-order__delete";
    deleteButton.type = "button";
    deleteButton.setAttribute("aria-label", `刪除行程紀錄：${order.trip.attraction.name}`);
    const deleteIcon = document.createElement("img");
    deleteIcon.src = "/static/images/icon_delete.png";
    deleteIcon.alt = "";
    deleteButton.append(deleteIcon);
    deleteButton.addEventListener("click", () => openDeleteDialog(order));

    const details = document.createElement("div");
    details.className = "member-order__details";
    const time = order.trip.time === "morning" ? "早上 9 點到下午 4 點" : "下午 2 點到晚上 9 點";
    const rows = [
      ["訂單編號", order.number],
      ["台北一日遊", order.trip.attraction.name],
      ["日期", order.trip.date],
      ["時間", time],
      ["地點", order.trip.attraction.address],
      ["費用", `新台幣 ${order.price} 元`],
      ["聯絡人", order.contact.name],
      ["聯絡信箱", order.contact.email],
      ["手機號碼", order.contact.phone],
    ];
    rows.forEach(([label, value], index) => {
      const line = document.createElement(index === 1 ? "h3" : "p");
      const strong = document.createElement("strong");
      strong.textContent = `${label}：`;
      line.append(strong, document.createTextNode(value || "—"));
      details.append(line);
    });
    card.append(image, details, deleteButton);
    ordersList.append(card);
  });
}

function openDeleteDialog(order) {
  orderPendingDeletion = order;
  deleteOrderText.textContent = `${order.trip.attraction.name}（訂單編號：${order.number}）`;
  deleteMessage.textContent = "";
  deleteDialog.hidden = false;
  document.body.style.overflow = "hidden";
  deleteCancel.focus();
}

function closeDeleteDialog() {
  if (deleteConfirm.disabled) return;
  deleteDialog.hidden = true;
  document.body.style.overflow = "";
  orderPendingDeletion = null;
}

async function confirmDeleteOrder() {
  if (!orderPendingDeletion) return;
  deleteConfirm.disabled = true;
  deleteCancel.disabled = true;
  deleteMessage.textContent = "刪除中...";
  try {
    const response = await fetch(`/api/member/orders/${encodeURIComponent(orderPendingDeletion.number)}`, {
      method: "DELETE",
      headers: { Accept: "application/json", ...window.auth.authHeaders() },
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.message || "刪除行程紀錄失敗");
    deleteDialog.hidden = true;
    document.body.style.overflow = "";
    orderPendingDeletion = null;
    ordersStatus.textContent = "行程紀錄已刪除";
    await loadOrders();
  } catch (error) {
    deleteMessage.textContent = error.message;
  } finally {
    deleteConfirm.disabled = false;
    deleteCancel.disabled = false;
  }
}

async function loadOrders() {
  try {
    const response = await fetch("/api/member/orders", {
      headers: { Accept: "application/json", ...window.auth.authHeaders() },
    });
    const payload = await response.json();
    if (!response.ok || !Array.isArray(payload.data)) throw new Error();
    renderOrders(payload.data);
  } catch (error) {
    ordersStatus.textContent = "已完成的行程載入失敗，請稍後再試";
  }
}

async function generateToken() {
  tokenButton.disabled = true;
  message.textContent = "";
  try {
    const response = await fetch("/api/member/token", {
      method: "PUT",
      headers: { Accept: "application/json", ...window.auth.authHeaders() },
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error();
    tokenOutput.textContent = payload.token;
    sessionStorage.setItem(MCP_TOKEN_SESSION_KEY, JSON.stringify({
      userId: signedInMember.id,
      token: payload.token,
    }));
    message.textContent = "新金鑰已產生；舊金鑰已失效。請立即複製並妥善保存。";
  } catch (error) {
    message.textContent = "金鑰產生失敗，請重新登入後再試。";
  } finally {
    tokenButton.disabled = false;
  }
}

function logout() {
  sessionStorage.removeItem(MCP_TOKEN_SESSION_KEY);
  localStorage.removeItem("token");
  window.location.replace("/");
}

tokenButton.addEventListener("click", generateToken);
logoutButton.addEventListener("click", logout);
deleteCancel.addEventListener("click", closeDeleteDialog);
deleteConfirm.addEventListener("click", confirmDeleteOrder);
deleteDialog.addEventListener("click", (event) => { if (event.target === deleteDialog) closeDeleteDialog(); });
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !deleteDialog.hidden) closeDeleteDialog();
});

window.addEventListener("auth:ready", async () => {
  const user = await requireMember();
  if (user) await Promise.all([loadOrders(), loadMcpConfig(user)]);
}, { once: true });

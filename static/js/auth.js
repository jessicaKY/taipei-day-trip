"use strict";

const AUTH_TOKEN_KEY = "token";

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function authHeaders() {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function createAuthDialog() {
  const overlay = document.createElement("div");
  overlay.className = "auth-overlay";
  overlay.hidden = true;
  overlay.innerHTML = `
    <section class="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
      <button class="auth-dialog__close" type="button" aria-label="關閉">
        <img src="/static/images/icon_close.png" alt="" />
      </button>
      <h2 id="auth-title">登入會員帳號</h2>
      <form class="auth-form" id="auth-form">
        <div id="auth-fields"></div>
        <button class="auth-form__submit" type="submit">登入帳戶</button>
        <button class="auth-dialog__switch" type="button">還沒有帳戶？點此註冊</button>
        <p class="auth-dialog__message" role="status" aria-live="polite"></p>
      </form>
    </section>`;
  document.body.append(overlay);
  return overlay;
}

const authUi = {
  mode: "signin",
  overlay: createAuthDialog(),
};

authUi.dialog = authUi.overlay.querySelector(".auth-dialog");
authUi.title = authUi.overlay.querySelector("#auth-title");
authUi.form = authUi.overlay.querySelector("#auth-form");
authUi.fields = authUi.overlay.querySelector("#auth-fields");
authUi.submit = authUi.overlay.querySelector(".auth-form__submit");
authUi.switchButton = authUi.overlay.querySelector(".auth-dialog__switch");
authUi.message = authUi.overlay.querySelector(".auth-dialog__message");
authUi.close = authUi.overlay.querySelector(".auth-dialog__close");

function renderAuthMode(mode) {
  authUi.mode = mode;
  const isSignin = mode === "signin";
  authUi.title.textContent = isSignin ? "登入會員帳號" : "註冊會員帳號";
  authUi.fields.innerHTML = isSignin
    ? `<input name="email" type="email" placeholder="輸入電子信箱" autocomplete="email" required />
       <input name="password" type="password" placeholder="輸入密碼" autocomplete="current-password" minlength="4" required />`
    : `<input name="name" type="text" placeholder="輸入姓名" autocomplete="name" required />
       <input name="email" type="email" placeholder="輸入電子信箱" autocomplete="email" required />
       <input name="password" type="password" placeholder="輸入密碼" autocomplete="new-password" minlength="4" required />`;
  authUi.fields.style.display = "flex";
  authUi.fields.style.flexDirection = "column";
  authUi.fields.style.gap = "10px";
  authUi.submit.textContent = isSignin ? "登入帳戶" : "註冊新帳戶";
  authUi.switchButton.textContent = isSignin ? "還沒有帳戶？點此註冊" : "已經有帳戶了？點此登入";
  authUi.message.textContent = "";
  authUi.message.classList.remove("auth-dialog__message--success");
  authUi.dialog.style.minHeight = isSignin ? "275px" : "332px";
}

function openAuthDialog(mode = "signin") {
  renderAuthMode(mode);
  authUi.overlay.hidden = false;
  document.body.style.overflow = "hidden";
  authUi.fields.querySelector("input")?.focus();
}

function closeAuthDialog() {
  authUi.overlay.hidden = true;
  document.body.style.overflow = "";
}

function showAuthMessage(message, success = false) {
  authUi.message.textContent = message;
  authUi.message.classList.toggle("auth-dialog__message--success", success);
}

async function parseApiResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message || "連線失敗，請稍後再試");
  return payload;
}

async function submitAuthForm(event) {
  event.preventDefault();
  if (!authUi.form.reportValidity()) return;
  const values = Object.fromEntries(new FormData(authUi.form));
  authUi.submit.disabled = true;
  showAuthMessage("");
  try {
    if (authUi.mode === "signup") {
      await parseApiResponse(await fetch("/api/user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      }));
      showAuthMessage("註冊成功，請登入系統", true);
      return;
    }
    const payload = await parseApiResponse(await fetch("/api/user/auth", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    }));
    localStorage.setItem(AUTH_TOKEN_KEY, payload.token);
    window.location.reload();
  } catch (error) {
    showAuthMessage(error.message);
  } finally {
    authUi.submit.disabled = false;
  }
}

async function checkAuthStatus() {
  const memberButton = document.querySelector(".navigation__member");
  if (!memberButton) return null;
  let user = null;
  try {
    const payload = await parseApiResponse(await fetch("/api/user/auth", {
      headers: { Accept: "application/json", ...authHeaders() },
    }));
    user = payload.data;
  } catch (error) {
    console.error(error);
  }
  if (!user) localStorage.removeItem(AUTH_TOKEN_KEY);
  memberButton.textContent = user ? "登出系統" : "登入/註冊";
  memberButton.onclick = () => {
    if (user) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      window.location.reload();
    } else {
      openAuthDialog("signin");
    }
  };
  window.currentUser = user;
  window.dispatchEvent(new CustomEvent("auth:ready", { detail: user }));
  return user;
}

authUi.form.addEventListener("submit", submitAuthForm);
authUi.switchButton.addEventListener("click", () => renderAuthMode(authUi.mode === "signin" ? "signup" : "signin"));
authUi.close.addEventListener("click", closeAuthDialog);
authUi.overlay.addEventListener("click", (event) => { if (event.target === authUi.overlay) closeAuthDialog(); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !authUi.overlay.hidden) closeAuthDialog(); });
checkAuthStatus();

window.auth = { authHeaders, checkAuthStatus, getAuthToken, openAuthDialog };

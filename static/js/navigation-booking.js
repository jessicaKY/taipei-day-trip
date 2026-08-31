"use strict";

const bookingNavigationLink = document.querySelector('.navigation__links a[href="/booking"]');

bookingNavigationLink?.addEventListener("click", async (event) => {
  event.preventDefault();
  const user = window.currentUser !== undefined ? window.currentUser : await window.auth.checkAuthStatus();
  if (user) window.location.href = "/booking";
  else window.auth.openAuthDialog("signin");
});

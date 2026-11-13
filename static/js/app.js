document.querySelectorAll('form').forEach(form => form.addEventListener('submit', event => {
  form.querySelectorAll('button[type="submit"]').forEach(button => {
    // A named submitter carries actions such as status=confirmed.
    if (button !== event.submitter || (!button.name && !button.hasAttribute('formaction'))) button.disabled = true;
  });
}));

document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (event.submitter?.hasAttribute('data-skip-confirm')) return;
    if (!window.confirm(form.dataset.confirm)) {
      event.preventDefault();
      event.stopImmediatePropagation();
    } else if (form.dataset.processing) {
      // Do not disable the clicked status button before form serialization:
      // disabled submitters lose their name/value and would drop the action.
      const button = event.submitter;
      if (button) button.textContent = form.dataset.processing;
    }
  }, true);
});
document.querySelectorAll('img[data-product-image]').forEach(img => img.addEventListener('error', () => {
  if (!img.src.endsWith('/static/img/product-placeholder.svg')) img.src = '/static/img/product-placeholder.svg';
}));

document.querySelectorAll('form[data-account-edit]').forEach(form => {
  form.addEventListener('submit', event => {
    const disabling = form.querySelector('[name="status"]')?.value === 'disabled' && form.dataset.currentStatus !== 'disabled';
    const resetting = Boolean(form.querySelector('[name="password"]')?.value);
    if ((disabling || resetting) && !window.confirm(
      disabling && resetting ? 'Bạn xác nhận vô hiệu hóa tài khoản và đặt lại mật khẩu?' :
      disabling ? 'Bạn xác nhận vô hiệu hóa tài khoản? Các phiên hiện tại sẽ bị thu hồi.' :
      'Bạn xác nhận đặt lại mật khẩu? Các phiên hiện tại sẽ bị thu hồi.'
    )) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
});

// Same-origin cookie-authenticated AJAX mutations use the synchronizer token.
const originalFetch = window.fetch.bind(window);
window.fetch = (input, init = {}) => {
  const url = new URL(input instanceof Request ? input.url : input, location.href);
  const method = (init.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
  if (url.origin === location.origin && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
    headers.set('X-CSRF-Token', document.querySelector('meta[name="csrf-token"]').content);
    init = { ...init, headers };
  }
  return originalFetch(input, init);
};


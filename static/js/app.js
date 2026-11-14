const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
if (sidebarToggle) {
  const setSidebarCollapsed = collapsed => {
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    const label = collapsed ? 'Mở rộng menu' : 'Thu gọn menu';
    sidebarToggle.setAttribute('aria-expanded', String(!collapsed));
    sidebarToggle.setAttribute('aria-label', label);
    sidebarToggle.title = label;
  };
  try { setSidebarCollapsed(sessionStorage.getItem('sidebar-collapsed') === 'true'); } catch (_) { /* Keep the default expanded menu. */ }
  sidebarToggle.addEventListener('click', () => {
    const collapsed = !document.body.classList.contains('sidebar-collapsed');
    setSidebarCollapsed(collapsed);
    try { sessionStorage.setItem('sidebar-collapsed', String(collapsed)); } catch (_) { /* Navigation still works without storage. */ }
  });
}

// Keep the successful submitter enabled: its name/value, formaction and
// formnovalidate must reach the browser unchanged (checkout uses all three).
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', event => {
    if (form.dataset.submitting === 'true') {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
  form.addEventListener('submit', event => {
    if (event.defaultPrevented) return;
    if (form.matches('[data-async-form]')) return;
    form.dataset.submitting = 'true';
    form.setAttribute('aria-busy', 'true');
    const submitter = event.submitter;
    // Wait until the browser serializes the clicked button's name and value.
    setTimeout(() => {
      form.querySelectorAll('button[type="submit"], button:not([type]), input[type="submit"]').forEach(button => {
        if (button.disabled) return;
        button.dataset.wasEnabled = 'true';
        button.disabled = true;
      });
      if (submitter && submitter.tagName === 'BUTTON') {
        submitter.dataset.originalMarkup = submitter.innerHTML;
        submitter.insertAdjacentHTML('afterbegin', '<span class="loading-spinner" aria-hidden="true"></span>');
      }
    }, 0);
  });
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('form[data-submitting]').forEach(form => {
    delete form.dataset.submitting;
    form.removeAttribute('aria-busy');
    form.querySelectorAll('[data-was-enabled]').forEach(button => { button.disabled = false; delete button.dataset.wasEnabled; });
    form.querySelectorAll('[data-original-markup]').forEach(button => { button.innerHTML = button.dataset.originalMarkup; delete button.dataset.originalMarkup; });
    form.querySelectorAll('[data-original-label]').forEach(button => {
      button.textContent = button.dataset.originalLabel;
      delete button.dataset.originalLabel;
    });
  });
});

document.querySelectorAll('[data-slideshow]').forEach(slideshow => {
  const slides = Array.from(slideshow.querySelectorAll('.catalog-slide'));
  if (slides.length < 2 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  let index = 0;
  setInterval(() => {
    if (document.hidden) return;
    slides[index].classList.remove('active');
    index = (index + 1) % slides.length;
    slides[index].classList.add('active');
  }, 4500);
});

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
      if (button) {
        button.dataset.originalLabel = button.textContent;
        button.textContent = form.dataset.processing;
      }
    }
  }, true);
});
document.querySelectorAll('img[data-product-image]').forEach(img => {
  const fallback = () => {
    if (!img.src.endsWith('/static/img/product-placeholder.svg')) img.src = '/static/img/product-placeholder.svg';
  };
  img.addEventListener('error', fallback);
  if (img.complete && img.naturalWidth === 0) fallback();
});
document.querySelectorAll('img[data-avatar-fallback]').forEach(img => {
  img.addEventListener('error', () => { img.src = '/static/img/avatar-default.svg'; }, { once: true });
});

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


// Accessible, optional password visibility; preserve autocomplete and input names.
document.querySelectorAll('[data-password-toggle]').forEach(button => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(visible));
    button.setAttribute('aria-label', `${visible ? 'Ẩn' : 'Hiện'} ${button.dataset.passwordLabel || 'mật khẩu'}`);
    button.textContent = visible ? 'Ẩn' : 'Hiện';
  });
});

// Keyboard users can scroll wide tables without scrolling the whole page.
document.querySelectorAll('.table-responsive').forEach(region => {
  region.tabIndex = 0;
  region.setAttribute('role', 'region');
  const heading = region.querySelector('thead');
  region.setAttribute('aria-label', heading ? `Bảng: ${heading.innerText.replace(/\s+/g, ' ').trim()}` : 'Bảng dữ liệu');
});

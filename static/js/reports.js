(() => {
  const sidebar = document.querySelector('.report-sidebar');
  const content = document.querySelector('.report-content');
  if (!sidebar || !content) return;

  let controller;

  const setActiveLink = url => {
    const selected = new URL(url, window.location.origin).searchParams.get('report');
    sidebar.querySelectorAll('.report-link').forEach(link => {
      const code = new URL(link.href, window.location.origin).searchParams.get('report');
      link.classList.toggle('active', code === selected);
      if (code === selected) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  };

  const loadReport = async (url, addHistory = true) => {
    controller?.abort();
    controller = new AbortController();
    content.classList.add('is-loading');
    content.setAttribute('aria-busy', 'true');
    content.querySelector('[data-report-error]')?.remove();

    try {
      const response = await fetch(url, {
        headers: { 'X-Requested-With': 'fetch' },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error('Không thể tải báo cáo');

      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const nextContent = page.querySelector('.report-content');
      if (!nextContent) throw new Error('Dữ liệu báo cáo không hợp lệ');

      content.replaceChildren(...nextContent.childNodes);
      content.querySelectorAll('.table-responsive').forEach(region => {
        region.tabIndex = 0;
        region.setAttribute('role', 'region');
        region.setAttribute('aria-label', 'Bảng dữ liệu báo cáo');
      });
      content.classList.remove('is-loading');
      content.removeAttribute('aria-busy');
      setActiveLink(url);
      if (addHistory) window.history.pushState({ report: true }, '', url);
    } catch (error) {
      if (error.name === 'AbortError') return;
      content.classList.remove('is-loading');
      content.removeAttribute('aria-busy');
      content.insertAdjacentHTML('afterbegin', '<div class="alert alert-danger m-3" role="alert" data-report-error>Không thể tải báo cáo. Vui lòng thử lại.</div>');
    }
  };

  sidebar.addEventListener('click', event => {
    const link = event.target.closest('.report-link');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (!link.classList.contains('active')) loadReport(link.href);
  });

  window.addEventListener('popstate', () => loadReport(window.location.href, false));
})();

// Independent requests keep drafts in the other forms on this page intact.
(() => {
  const forms = document.querySelectorAll('[data-async-form]');
  const avatar = document.getElementById('profile-avatar');
  const upload = document.getElementById('avatar-upload');
  const file = document.getElementById('avatar-file');
  const save = document.getElementById('avatar-save');
  const cancel = document.getElementById('avatar-cancel');
  const remove = document.getElementById('avatar-delete');
  document.getElementById('avatar-pick')?.addEventListener('click', () => file.click());
  let savedAvatar = avatar?.src;
  let selectionVersion = 0;
  let avatarBusy = false;

  function status(form, message, success = false) {
    const host = form.querySelector('[data-form-status]');
    host.textContent = message;
    host.className = `form-status alert ${success ? 'alert-success' : 'alert-danger'}`;
    host.setAttribute('role', success ? 'status' : 'alert');
    host.hidden = false;
  }

  function resetSelection() {
    selectionVersion++;
    if (!file) return;
    file.value = '';
    avatar.src = savedAvatar;
    save.disabled = true;
    save.hidden = true;
    cancel.hidden = true;
  }

  file?.addEventListener('change', async () => {
    const version = ++selectionVersion;
    const chosen = file.files[0];
    save.disabled = true;
    save.hidden = true;
    cancel.hidden = !chosen;
    avatar.src = savedAvatar;
    upload.querySelector('[data-form-status]').hidden = true;
    if (!chosen) return;
    if (!/\.(jpe?g|png|webp)$/i.test(chosen.name) || chosen.size > 800 * 1024 || !chosen.size) {
      status(upload, 'Chọn ảnh JPG, PNG hoặc WebP không quá 800 KiB.');
      return;
    }
    try {
      const source = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(chosen);
      });
      const preview = new Image();
      preview.src = source;
      await preview.decode();
      if (version !== selectionVersion) return;
      if (preview.naturalWidth * preview.naturalHeight > 16000000 || Math.max(preview.naturalWidth, preview.naturalHeight) > 8192) {
        throw new Error('oversized image');
      }
      avatar.src = source; // CSP already permits data: images; no uploaded markup is injected.
      save.disabled = false;
      save.hidden = false;
    } catch {
      if (version !== selectionVersion) return;
      status(upload, 'Không thể đọc ảnh hoặc ảnh vượt giới hạn 16 triệu pixel / 8192px mỗi cạnh.');
    }
  });
  cancel?.addEventListener('click', resetSelection);

  function clearPasswords(form) {
    form.querySelectorAll('input[name$="Password"]').forEach(input => {
      input.value = '';
      input.type = 'password';
      input.setCustomValidity('');
    });
    form.querySelectorAll('[data-password-toggle]').forEach(button => {
      button.textContent = 'Hiện';
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', `Hiện ${button.dataset.passwordLabel}`);
    });
  }

  const passwordForm = document.getElementById('password-form');
  if (passwordForm) {
    const current = passwordForm.elements.currentPassword;
    const next = passwordForm.elements.newPassword;
    const confirmation = passwordForm.elements.confirmPassword;
    const validate = () => {
      next.setCustomValidity(next.value && next.value === current.value ? 'Mật khẩu mới phải khác mật khẩu hiện tại.' : '');
      confirmation.setCustomValidity(confirmation.value && confirmation.value !== next.value ? 'Xác nhận mật khẩu mới chưa khớp.' : '');
    };
    [current, next, confirmation].forEach(input => input.addEventListener('input', validate));
  }

  forms.forEach(form => {
    form.addEventListener('reset', () => {
      form.querySelector('[data-form-status]').hidden = true;
    });
    form.addEventListener('submit', async event => {
      if (event.defaultPrevented) return; // Preserve the existing confirmation dialog.
      event.preventDefault();
      const kind = form.dataset.formKind;
      if (form.dataset.submitting === 'true' || (kind.startsWith('avatar') && avatarBusy)) return;
      // Capture fields before disabling any upload input; preserve the submitter.
      const body = new FormData(form, event.submitter);
      form.dataset.submitting = 'true';
      form.setAttribute('aria-busy', 'true');
      if (kind.startsWith('avatar')) { avatarBusy = true; file.disabled = true; cancel.disabled = true; }
      try {
        const reply = await fetch(form.action, { method: 'POST', body, headers: { Accept: 'application/json' } });
        let result;
        try { result = await reply.json(); }
        catch { throw new Error('Phiên có thể đã hết hạn hoặc yêu cầu chưa hợp lệ. Hãy tải lại trang sau khi lưu nội dung đang nhập.'); }
        if (!reply.ok || !result.success) throw new Error(result.message || 'Chưa thể lưu thay đổi. Vui lòng thử lại.');
        if (kind === 'password') { clearPasswords(form); window.location.assign('/login'); return; }
        if (kind === 'profile') {
          document.getElementById('profile-name').textContent = result.data.fullName;
          Object.entries(result.data).forEach(([name, value]) => {
            const input = form.elements.namedItem(name);
            if (!input) return;
            input.value = value;
            if (input.tagName === 'SELECT') Array.from(input.options).forEach(option => { option.defaultSelected = option.value === value; });
            else input.defaultValue = value;
          });
        }
        if (kind.startsWith('avatar')) {
          savedAvatar = `${result.data.avatarUrl}?v=${Date.now()}`;
          resetSelection();
          remove.hidden = !result.data.hasAvatar;
        }
        status(form, result.message, true);
      } catch (error) {
        if (kind === 'password') clearPasswords(form);
        status(form, error.message);
      } finally {
        delete form.dataset.submitting;
        form.removeAttribute('aria-busy');
        if (kind.startsWith('avatar')) { avatarBusy = false; file.disabled = false; cancel.disabled = false; }
      }
    }, true);
  });
})();

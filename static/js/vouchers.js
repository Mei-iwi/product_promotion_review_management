document.querySelectorAll('[data-copy-voucher]').forEach(button => {
  button.addEventListener('click', async () => {
    const card = button.closest('.voucher-ticket');
    const code = card.querySelector('.voucher-code-row code');
    const feedback = card.querySelector('[data-copy-feedback]');
    try {
      await navigator.clipboard.writeText(code.textContent.trim());
      feedback.textContent = `Đã sao chép mã ${code.textContent.trim()}.`;
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(code);
      selection.removeAllRanges();
      selection.addRange(range);
      feedback.textContent = 'Mã đã được chọn. Bạn có thể sao chép bằng Ctrl+C hoặc nhấn giữ trên điện thoại.';
    }
    feedback.hidden = false;
  });
});

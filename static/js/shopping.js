// Reprice committed quantity/code changes using the existing server forms.
// requestSubmit preserves CSRF, submitter, formaction and formnovalidate.
// Checkout always uses the promotion button, never the place-order button.
document.querySelectorAll('[data-auto-price]').forEach(field => {
  let appliedValue = field.value;
  field.addEventListener('change', () => {
    if (field.value === appliedValue || !field.checkValidity()) return;
    const form = field.form;
    if (!form || form.dataset.submitting === 'true') return;
    const submitter = form.querySelector('[data-promotion-submit]') || form.querySelector('button[type="submit"]');
    if (submitter?.disabled) return;
    appliedValue = field.value;
    if (submitter) form.requestSubmit(submitter);
    else form.requestSubmit();
  });
});

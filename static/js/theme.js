function getCsrfToken() {
  return document.querySelector('#theme-csrf-token input[name="csrfmiddlewaretoken"]')?.value || '';
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.querySelectorAll('[data-theme-choice]').forEach(card => {
    const selected = card.dataset.themeChoice === theme;
    card.classList.toggle('selected', selected);
    card.setAttribute('aria-pressed', String(selected));
    const indicator = card.querySelector('.selection-indicator');
    if (indicator) indicator.textContent = selected ? 'Selected' : 'Select';
  });
}

document.querySelectorAll('input[type="password"]').forEach((passwordInput, index) => {
  if (!passwordInput.id) passwordInput.id = `password-field-${index}`;
  passwordInput.classList.add('form-control');
  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'btn btn-sm btn-outline-secondary mt-2 password-toggle';
  toggle.textContent = 'Show password';
  toggle.setAttribute('aria-controls', passwordInput.id);
  toggle.setAttribute('aria-pressed', 'false');
  toggle.addEventListener('click', () => {
    const showing = passwordInput.type === 'text';
    passwordInput.type = showing ? 'password' : 'text';
    toggle.textContent = showing ? 'Show password' : 'Hide password';
    toggle.setAttribute('aria-pressed', String(!showing));
    passwordInput.focus();
  });
  passwordInput.insertAdjacentElement('afterend', toggle);
});

const themeGrid = document.querySelector('.theme-grid');
if (themeGrid) {
  themeGrid.addEventListener('click', async event => {
    const card = event.target.closest('[data-theme-choice]');
    if (!card) return;
    const previousTheme = document.documentElement.dataset.theme;
    const selectedTheme = card.dataset.themeChoice;
    applyTheme(selectedTheme);
    const status = document.querySelector('#theme-status');
    try {
      const response = await fetch(themeGrid.dataset.themeSaveUrl, {
        method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type':'application/json', 'X-CSRFToken':getCsrfToken()},
        body: JSON.stringify({theme:selectedTheme}),
      });
      const contentType = response.headers.get('content-type') || '';
      const payload = contentType.includes('application/json') ? await response.json() : {};
      if (!response.ok) throw new Error(payload.error?.message || 'Theme could not be saved.');
      status.className = 'alert alert-success';
      status.textContent = 'Theme saved successfully.';
    } catch (error) {
      applyTheme(previousTheme);
      status.className = 'alert alert-danger';
      status.textContent = error.message;
    }
  });
}

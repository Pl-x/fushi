(() => {
  const storageKey = 'lets-review-theme';
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const savedTheme = localStorage.getItem(storageKey);

  const applyTheme = theme => {
    document.body.classList.toggle('theme-dark', theme === 'dark');
    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
      const isDark = theme === 'dark';
      toggle.textContent = isDark ? '☀' : '☾';
      toggle.title = isDark ? 'Use light mode' : 'Use dark mode';
      toggle.setAttribute('aria-label', toggle.title);
      toggle.setAttribute('aria-pressed', String(isDark));
    }
  };

  const initialTheme = savedTheme || (prefersDark ? 'dark' : 'light');
  document.addEventListener('DOMContentLoaded', () => {
    applyTheme(initialTheme);
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'theme-toggle';
    toggle.onclick = () => {
      const nextTheme = document.body.classList.contains('theme-dark') ? 'light' : 'dark';
      localStorage.setItem(storageKey, nextTheme);
      applyTheme(nextTheme);
    };
    document.body.append(toggle);
    applyTheme(initialTheme);
  });
})();

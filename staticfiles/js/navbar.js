/**
 * Close mobile navbar after clicking a link (Bootstrap 5 collapse).
 */
(function () {
  const navMenu = document.getElementById('navMenu');
  if (!navMenu || typeof bootstrap === 'undefined') return;

  const collapse = bootstrap.Collapse.getOrCreateInstance(navMenu, { toggle: false });

  navMenu.querySelectorAll('.nav-link, .agro-nav-actions .btn').forEach((el) => {
    el.addEventListener('click', () => {
      if (window.innerWidth < 1200 && navMenu.classList.contains('show')) {
        collapse.hide();
      }
    });
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth >= 1200 && navMenu.classList.contains('show')) {
      collapse.hide();
    }
  });
})();

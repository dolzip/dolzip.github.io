"use strict";
const navigation = document.querySelector('.navigation');
const languages = document.querySelector('.languages');
const narrow = matchMedia('(max-width: 800px)');
function syncNavigation() { if (navigation) navigation.open = !narrow.matches; }
syncNavigation();
narrow.addEventListener('change', syncNavigation);
function closeMenu(menu, restoreFocus = false) {
  if (!menu) return;
  menu.open = false;
  if (restoreFocus) menu.querySelector('summary').focus();
}
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  if (languages?.open) closeMenu(languages, true);
  else if (narrow.matches && navigation?.open) closeMenu(navigation, true);
});
document.addEventListener('click', event => {
  if (languages?.open && !languages.contains(event.target)) closeMenu(languages);
  if (narrow.matches && navigation?.open && (!navigation.contains(event.target) || event.target.closest('nav a'))) closeMenu(navigation);
});
languages?.addEventListener('toggle', () => {
  if (languages.open && narrow.matches) closeMenu(navigation);
});
navigation?.addEventListener('toggle', () => {
  if (navigation.open && narrow.matches) closeMenu(languages);
});

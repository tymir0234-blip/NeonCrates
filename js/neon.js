const SLOT_W = 134;
const DURATION = 5200;

function getCookie(name) {
  const m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
  return m ? decodeURIComponent(m[2]) : null;
}

function setBalance(value) {
  const box = document.getElementById('balanceBox');
  if (!box) return;
  box.textContent = '⬡ ' + value.toLocaleString('ru-RU') + ' NEON';
  box.classList.remove('flash');
  void box.offsetWidth;
  box.classList.add('flash');
}

function showToast(name, price, image) {
  const toast = document.getElementById('dropToast');
  if (!toast) return;
  document.getElementById('dropToastName').textContent = name;
  document.getElementById('dropToastPrice').textContent = price.toLocaleString('ru-RU') + ' NEON';
  const img = document.getElementById('dropToastImg');
  img.src = image;
  toast.hidden = false;
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => { toast.hidden = true; }, 6000);
}

window.neon = { setBalance, showToast };
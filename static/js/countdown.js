// Таймер рассчитывается по времени СЕРВЕРА, а не по часам устройства.
(function () {
  const el = document.getElementById('countdown');
  if (!el) return;

  const target = Date.parse(el.dataset.target);
  // разница между часами сервера и браузера
  const offset = Date.parse(el.dataset.now) - Date.now();
  const dayLabel = el.dataset.day || 'd';
  let timer = null;

  function pad(n) { return String(n).padStart(2, '0'); }

  function tick() {
    let left = Math.floor((target - (Date.now() + offset)) / 1000);
    if (left <= 0) {
      el.textContent = '00:00:00';
      el.classList.add('text-danger');
      if (timer) clearInterval(timer);
      return;
    }
    const d = Math.floor(left / 86400); left %= 86400;
    const h = Math.floor(left / 3600); left %= 3600;
    const m = Math.floor(left / 60);
    const s = left % 60;
    el.textContent = (d > 0 ? d + dayLabel + ' ' : '') + pad(h) + ':' + pad(m) + ':' + pad(s);
  }

  tick();
  timer = setInterval(tick, 1000);
})();
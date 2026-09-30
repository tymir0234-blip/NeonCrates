(function () {
  const shell = document.getElementById('roulette');
  const track = document.getElementById('rouletteTrack');
  const resultBox = document.getElementById('rouletteResult');
  const pointerBox = document.querySelector('.roulette-window');

  const SLOT_W = 134;
  const DURATION = 5400;
  const WIN_INDEX = 54;
  const TAIL = 8;

  const btn = document.querySelector('[data-open-case]');
  if (!shell || !track || !resultBox || !pointerBox || !btn) return;

  let busy = false;

  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[2]) : null;
  }

  function slot(item, isWin) {
    const el = document.createElement('div');
    el.className = 'rslot' + (isWin ? ' win' : '');

    const img = document.createElement('img');
    img.src = item.image;
    img.alt = item.name;
    img.loading = 'lazy';

    const name = document.createElement('div');
    name.className = 'rs-name';
    name.textContent = item.name;

    const price = document.createElement('div');
    price.className = 'rs-price';
    price.textContent = item.price.toLocaleString('ru-RU') + ' NEON';

    el.append(img, name, price);
    return el;
  }

  function showResult(winItem, balance) {
    document.getElementById('resultImg').src = winItem.image;
    document.getElementById('resultName').textContent = winItem.name;
    document.getElementById('resultPrice').textContent =
      winItem.price.toLocaleString('ru-RU') + ' NEON';
    resultBox.hidden = false;
    if (balance !== null && balance !== undefined && window.neon) {
      window.neon.setBalance(balance);
    }
    if (window.neon) window.neon.showToast(winItem.name, winItem.price, winItem.image);
  }

  function spin(data) {
    shell.hidden = false;
    resultBox.hidden = true;
    resultBox.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    track.innerHTML = '';

    const winItem = data.skin;
    const decoys = data.strip.filter((i) => i.id !== winItem.id);
    while (decoys.length < WIN_INDEX + TAIL) {
      decoys.push(decoys[Math.floor(Math.random() * decoys.length)]);
    }

    decoys.slice(0, WIN_INDEX)
      .concat([winItem])
      .concat(decoys.slice(WIN_INDEX, WIN_INDEX + TAIL))
      .forEach((item, i) => track.appendChild(slot(item, i === WIN_INDEX)));

    const center = pointerBox.getBoundingClientRect().width / 2;
    const targetX = center - (WIN_INDEX * SLOT_W + SLOT_W / 2);

    track.style.transition = 'none';
    track.style.transform = `translateX(${center + pointerBox.clientWidth}px)`;

    void track.offsetWidth;

    let fallback = setTimeout(() => {
      track.removeEventListener('transitionend', onDone);
      finish();
    }, DURATION + 500);

    function onDone(e) {
      if (e.target !== track || e.propertyName !== 'transform') return;
      clearTimeout(fallback);
      track.removeEventListener('transitionend', onDone);
      finish();
    }

    function finish() {
      showResult(winItem, data.new_balance);
      busy = false;
      btn.disabled = false;
      btn.textContent = 'Открыть кейс';
    }

    track.addEventListener('transitionend', onDone);
    track.style.transition = `transform ${DURATION}ms cubic-bezier(0.14, 0.85, 0.15, 1)`;
    track.style.transform = `translateX(${targetX}px)`;
  }

  btn.addEventListener('click', async function () {
    if (busy) return;
    busy = true;
    btn.disabled = true;
    btn.textContent = 'Открываем…';

    try {
      const res = await fetch(`/api/open/${btn.dataset.openCase}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      });
      const data = await res.json();

      if (data.error === 'auth') {
        window.location.href = '/auth/login/?next=' +
          encodeURIComponent(window.location.pathname);
        return;
      }
      if (data.error === 'not_enough_balance') {
        alert('Недостаточно средств. Активируйте промокод в профиле.');
        busy = false;
        btn.disabled = false;
        btn.textContent = 'Открыть кейс';
        return;
      }
      spin(data);
    } catch (err) {
      busy = false;
      btn.disabled = false;
      btn.textContent = 'Открыть кейс';
    }
  });
})();
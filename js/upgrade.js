(function () {
  const form = document.getElementById('upgForm');
  if (!form) return;

  const itemInput = document.getElementById('upgItem');
  const caseSel = document.getElementById('upgCase');
  const ratioSel = document.getElementById('upgRatio');
  const submit = document.getElementById('upgSubmit');
  const wheelWrap = document.getElementById('wheelWrap');
  const wheelEmpty = document.getElementById('wheelEmpty');
  const canvas = document.getElementById('wheel');
  const hubImg = document.getElementById('wheelHubImg');
  const hubText = document.getElementById('wheelHubText');
  const sumItem = document.getElementById('sumItem');
  const sumThreshold = document.getElementById('sumThreshold');
  const sumCount = document.getElementById('sumCount');

  let spinning = false;

  function fmt(n) {
    return Math.round(n).toLocaleString('ru-RU');
  }

  function selected() {
    const el = form.querySelector('input[name="item_choice"]:checked');
    if (!el) return null;
    return {
      id: el.value,
      price: parseFloat(el.dataset.price),
      name: el.dataset.name,
      image: el.dataset.image,
    };
  }

  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[2]) : null;
  }

  function refresh() {
    const item = selected();
    submit.disabled = true;
    submit.textContent = 'Улучшить';
    if (!item) {
      itemInput.value = '';
      wheelEmpty.textContent = 'Выберите предмет и кейс — шансы появятся здесь.';
      wheelEmpty.hidden = false;
      wheelWrap.hidden = true;
      hubImg.src = '';
      hubText.textContent = '—';
      return;
    }
    itemInput.value = item.id;
    sumItem.textContent = fmt(item.price);

    const body = new URLSearchParams({
      case: caseSel.value,
      ratio: ratioSel.value,
      item: item.id,
    });

    fetch('/api/upgrade/preview/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body,
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) return;
        sumThreshold.textContent = fmt(data.threshold);
        sumCount.textContent = data.segments.length;
        submit.disabled = !data.possible;
        submit.textContent = data.possible ? 'Улучшить' : 'Недостижимый коэффициент';

        if (!data.possible) {
          wheelEmpty.textContent =
            'В кейсе нет предметов от ' + fmt(data.threshold) +
            ' NEON. Уменьшите коэффициент или возьмите другой кейс.';
          wheelEmpty.hidden = false;
          wheelWrap.hidden = true;
          return;
        }

        wheelEmpty.hidden = true;
        wheelWrap.hidden = false;
        hubImg.src = item.image;
        hubText.textContent = fmt(item.price) + ' NEON';

        NeonWheel.render(canvas, data.segments, null);
      });
  }

  form.addEventListener('change', function (e) {
    if (
      e.target.matches('input[name="item_choice"]') ||
      e.target === caseSel ||
      e.target === ratioSel
    ) {
      refresh();
    }
  });

  form.addEventListener('submit', function (e) {
    const item = selected();
    if (!item) {
      e.preventDefault();
      return;
    }
    if (spinning) {
      e.preventDefault();
      return;
    }
    spinning = true;
    submit.disabled = true;
    submit.textContent = 'Крутим…';

    const body = new URLSearchParams({
      case: caseSel.value,
      ratio: ratioSel.value,
      item: item.id,
    });
    const token = getCookie('csrftoken');

    fetch('/api/upgrade/roll/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': token,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body,
    })
      .then((r) => r.json().then((d) => [d, r.status]))
      .then(([result, status]) => {
        if (status !== 200 || result.error) {
          alert(result.error || 'Не удалось выполнить апгрейд.');
          spinning = false;
          refresh();
          return;
        }

        NeonWheel.spin(canvas, result.wheel.segments, result.winner.id, () => {
          hubImg.src = result.winner.image;
          hubText.textContent = fmt(result.winner.price) + ' NEON';
          if (window.neon && result.new_balance !== null) {
            window.neon.setBalance(result.new_balance);
          }
          setTimeout(() => {
            window.location.reload();
          }, 1100);
        });
      })
      .catch(() => {
        spinning = false;
        refresh();
      });
  });

  refresh();
})();
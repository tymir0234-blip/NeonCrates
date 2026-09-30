window.NeonWheel = (function () {
  const TAU = Math.PI * 2;
  const COLORS = [
    '#00f0ff', '#8b5cff', '#ff2fb9', '#38ffb0', '#ffd75c',
    '#4d7cff', '#ff7a5c', '#5ce1b8', '#c86bff', '#ff9ecd',
  ];

  let state = { segments: [], rotation: 0, angle: 0 };

  function draw(canvas, rotation) {
    const ctx = canvas.getContext('2d');
    const size = canvas.width;
    const cx = size / 2;
    const cy = size / 2;
    const r = size / 2 - 6;

    ctx.clearRect(0, 0, size, size);

    const segs = state.segments;
    if (!segs.length) return;

    let start = -Math.PI / 2 + rotation;
    segs.forEach((s, i) => {
      const sweep = (s.chance / 100) * TAU;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, start, start + sweep);
      ctx.closePath();
      ctx.fillStyle = COLORS[i % COLORS.length];
      ctx.globalAlpha = s.id === state.winnerId ? 1 : 0.55;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.lineWidth = 2;
      ctx.strokeStyle = 'rgba(8,6,18,0.9)';
      ctx.stroke();

      if (sweep > 0.22) {
        const mid = start + sweep / 2;
        ctx.save();
        ctx.translate(cx + Math.cos(mid) * r * 0.66, cy + Math.sin(mid) * r * 0.66);
        ctx.rotate(mid + Math.PI / 2);
        ctx.fillStyle = '#0a0718';
        ctx.font = '600 12px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(s.chance.toFixed(1) + '%', 0, 0);
        ctx.restore();
      }

      start += sweep;
    });

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, TAU);
    ctx.lineWidth = 3;
    ctx.strokeStyle = 'rgba(255,255,255,0.22)';
    ctx.stroke();
  }

  function render(canvas, segments, winnerId) {
    state = { segments: segments || [], rotation: 0, angle: 0, winnerId: winnerId };
    draw(canvas, 0);
  }

  function findSegmentByAngle(segments, targetAngle) {
    let acc = 0;
    const deg = ((targetAngle % 360) + 360) % 360;
    for (let i = 0; i < segments.length; i++) {
      const sweep = (segments[i].chance / 100) * 360;
      const nextAcc = acc + sweep;
      if (deg >= acc && deg < nextAcc) return i;
      acc = nextAcc;
    }
    return 0;
  }

  function spin(canvas, segments, winnerId, done) {
    const index = segments.findIndex((s) => s.id === winnerId);
    if (index < 0) return;

    let acc = 0;
    for (let i = 0; i < index; i++) acc += (segments[i].chance / 100) * 360;
    const sweep = (segments[index].chance / 100) * 360;
    const mid = acc + sweep / 2;

    state.winnerId = winnerId;
    const startRotation = state.rotation || 0;
    const turns = 5 + Math.floor(Math.random() * 3);
    const jitter = (Math.random() - 0.5) * sweep * 0.5;
    const target = 360 - (mid + jitter);
    const from = startRotation - (startRotation % 360);
    const finalAngle = from + turns * 360 + target;

    const t0 = performance.now();
    const dur = 4200;
    const ease = (t) => 1 - Math.pow(1 - t, 4);

    function frame(now) {
      const t = Math.min((now - t0) / dur, 1);
      state.rotation = startRotation + (finalAngle - startRotation) * ease(t);
      draw(canvas, state.rotation);
      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        if (done) done();
      }
    }
    requestAnimationFrame(frame);
  }

  return { render, spin, draw, findSegmentByAngle };
})();
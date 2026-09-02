(() => {
  const data = window.DEMO_DATA;
  const canvas = document.querySelector('#stage');
  const ctx = canvas.getContext('2d');
  const timeline = document.querySelector('#timeline');
  const play = document.querySelector('#play');
  const reset = document.querySelector('#reset');
  const speed = document.querySelector('#speed');
  const scene = data.scenario;
  const trajectory = data.trajectory;
  let index = 0;
  let playing = false;
  let last = 0;

  timeline.max = trajectory.length - 1;
  document.querySelector('#route').textContent = `${data.metrics.route_length} m`;
  document.querySelector('#clearance').textContent = `${data.metrics.minimum_clearance} m`;

  function point(x, y) {
    const pad = 34;
    return [pad + x * ((canvas.width - pad * 2) / scene.width), pad + y * ((canvas.height - pad * 2) / scene.height)];
  }

  function drawPath(points, color, width, dashed = false, until = points.length) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    if (dashed) ctx.setLineDash([9, 8]);
    ctx.beginPath();
    points.slice(0, until).forEach((p, i) => {
      const [x, y] = point(p.x ?? p[0], p.y ?? p[1]);
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    });
    ctx.stroke();
    ctx.restore();
  }

  function draw() {
    ctx.fillStyle = '#f1f6fc';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const [x0, y0] = point(0, 0);
    const [x1, y1] = point(1, 1);
    const cellW = x1 - x0;
    const cellH = y1 - y0;

    ctx.fillStyle = '#d4dfec';
    scene.blocked.forEach(([x, y]) => {
      const [px, py] = point(x, y);
      ctx.fillRect(px, py, cellW + .5, cellH + .5);
    });

    drawPath(data.global_path, '#4c8dff', 5, true);
    drawPath(trajectory, '#22baa9', 7, false, index + 1);

    scene.dynamic_obstacles.forEach(o => {
      if (index < o.appears_at_step) return;
      const [x, y] = point(o.x, o.y);
      ctx.beginPath();
      ctx.arc(x, y, o.radius * cellW, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,109,121,.24)';
      ctx.fill();
      ctx.strokeStyle = '#ff6d79';
      ctx.lineWidth = 3;
      ctx.stroke();
    });

    const robot = trajectory[index];
    const [rx, ry] = point(robot.x, robot.y);
    ctx.save();
    ctx.translate(rx, ry);
    ctx.rotate(robot.yaw);
    ctx.fillStyle = '#081427';
    ctx.shadowColor = 'rgba(8,20,39,.3)';
    ctx.shadowBlur = 14;
    ctx.beginPath();
    ctx.roundRect(-14, -10, 28, 20, 6);
    ctx.fill();
    ctx.fillStyle = '#43dac9';
    ctx.beginPath();
    ctx.moveTo(18, 0); ctx.lineTo(8, -6); ctx.lineTo(8, 6); ctx.closePath(); ctx.fill();
    ctx.restore();

    const pct = Math.round(index / (trajectory.length - 1) * 100);
    document.querySelector('#progress').textContent = `${pct}%`;
    document.querySelector('#status').textContent = index === trajectory.length - 1 ? '已到达' : index >= scene.dynamic_obstacles[0].appears_at_step ? '动态避障' : '路径跟随';
    timeline.value = index;
  }

  function frame(timestamp) {
    if (!playing) return;
    const interval = 90 / Number(speed.value);
    if (timestamp - last >= interval) {
      index = Math.min(index + 1, trajectory.length - 1);
      last = timestamp;
      draw();
      if (index === trajectory.length - 1) {
        playing = false;
        play.textContent = '↺ 重播';
        return;
      }
    }
    requestAnimationFrame(frame);
  }

  play.addEventListener('click', () => {
    if (index === trajectory.length - 1) index = 0;
    playing = !playing;
    play.textContent = playing ? 'Ⅱ 暂停' : '▶ 播放';
    if (playing) requestAnimationFrame(frame);
  });
  reset.addEventListener('click', () => { playing = false; index = 0; play.textContent = '▶ 播放'; draw(); });
  timeline.addEventListener('input', e => { index = Number(e.target.value); playing = false; play.textContent = '▶ 播放'; draw(); });
  draw();
})();

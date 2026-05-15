let chart;
const pnlHistory = { labels: [], scalping: [], arbitrage: [], total: [] };
let activeTab = 'all';

function initChart() {
  const ctx = document.getElementById('pnl-chart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: pnlHistory.labels,
      datasets: [
        { label: 'Total', data: pnlHistory.total, borderColor: '#58a6ff', tension: 0.2, pointRadius: 0 },
        { label: 'Scalping', data: pnlHistory.scalping, borderColor: '#3fb950', tension: 0.2, pointRadius: 0 },
        { label: 'Arbitrage', data: pnlHistory.arbitrage, borderColor: '#d2a8ff', tension: 0.2, pointRadius: 0 },
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#e6edf3' } } },
      scales: {
        x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
        y: { ticks: { color: '#8b949e', callback: v => '$' + v.toFixed(2) }, grid: { color: '#21262d' } }
      }
    }
  });
}

function formatPnl(val) {
  const cls = val >= 0 ? 'pnl-positive' : 'pnl-negative';
  return `<span class="${cls}">${val >= 0 ? '+' : ''}$${val.toFixed(4)}</span>`;
}

async function refreshPerformance() {
  const data = await fetch('/api/performance').then(r => r.json());
  document.getElementById('total-pnl').innerHTML = formatPnl(data.total_pnl);
  document.getElementById('win-rate').textContent = `Win rate: ${data.win_rate.toFixed(1)}%`;
  document.getElementById('scalping-pnl').innerHTML = formatPnl(data.scalping.pnl);
  document.getElementById('scalping-trades').textContent = `${data.scalping.total} trades`;
  document.getElementById('arb-pnl').innerHTML = formatPnl(data.arbitrage.pnl);
  document.getElementById('arb-trades').textContent = `${data.arbitrage.total} trades`;
  const now = new Date().toLocaleTimeString();
  pnlHistory.labels.push(now);
  pnlHistory.total.push(data.total_pnl);
  pnlHistory.scalping.push(data.scalping.pnl);
  pnlHistory.arbitrage.push(data.arbitrage.pnl);
  if (pnlHistory.labels.length > 120) {
    ['labels','total','scalping','arbitrage'].forEach(k => pnlHistory[k].shift());
  }
  chart.update();
}

async function refreshTrades() {
  const strategy = activeTab === 'all' ? '' : `strategy=${activeTab}&`;
  const trades = await fetch(`/api/trades?${strategy}limit=50`).then(r => r.json());
  const body = document.getElementById('trades-body');
  if (!trades.length) {
    body.innerHTML = '<tr><td colspan="8" class="text-muted">No trades yet</td></tr>';
    return;
  }
  body.innerHTML = trades.map(t => `
    <tr>
      <td>${t.opened_at ? t.opened_at.slice(11,19) : '--'}</td>
      <td><span class="badge bg-secondary">${t.strategy}</span></td>
      <td class="text-truncate" style="max-width:120px">${t.market_id}</td>
      <td>${t.side}</td>
      <td>${t.size.toFixed(2)}</td>
      <td>${t.entry_price.toFixed(3)}</td>
      <td>${t.exit_price != null ? t.exit_price.toFixed(3) : '--'}</td>
      <td>${t.realized_pnl != null ? formatPnl(t.realized_pnl) : '--'}</td>
    </tr>`).join('');
}

async function refreshPositions() {
  const positions = await fetch('/api/positions').then(r => r.json());
  const body = document.getElementById('positions-body');
  if (!positions.length) {
    body.innerHTML = '<tr><td colspan="6" class="text-muted">No open positions</td></tr>';
    return;
  }
  body.innerHTML = positions.map(p => `
    <tr>
      <td><span class="badge bg-secondary">${p.strategy}</span></td>
      <td class="text-truncate" style="max-width:120px">${p.market_id}</td>
      <td>${p.side}</td>
      <td>${p.size.toFixed(2)}</td>
      <td>${p.entry_price.toFixed(3)}</td>
      <td>${p.current_price != null ? p.current_price.toFixed(3) : '--'}</td>
    </tr>`).join('');
}

async function refresh() {
  await Promise.all([refreshPerformance(), refreshTrades(), refreshPositions()]);
}

document.querySelectorAll('[data-tab]').forEach(el => {
  el.addEventListener('click', e => {
    e.preventDefault();
    activeTab = el.dataset.tab;
    document.querySelectorAll('[data-tab]').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    refreshTrades();
  });
});

initChart();
refresh();
setInterval(refresh, 5000);

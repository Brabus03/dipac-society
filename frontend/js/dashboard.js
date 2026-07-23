const rupiah = n => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n);
const staticDashboard = {
  user: { name: 'DIPAC Administrator' }, totals: { revenue: 225800000, profit: 84800000, pax: 1556, transactions: 855 },
  events: [{ name: 'Dentra TNF Semarang', event_date: '2026-05-01', location: 'Semarang', category: 'Event archive', pax: 0, total_revenue: 0, total_profit: 0 }, { name: 'Midnight In Cell Soci Semarang', event_date: '2026-05-19', location: 'Semarang', category: 'Event archive', pax: 0, total_revenue: 0, total_profit: 0 }],
  insights: [{ recommendation: 'Jalankan aplikasi dengan python3 app.py untuk mengimpor dan menganalisis report PDF.', name: 'DIPAC Society' }], reports: []
};

function renderDashboard(d) {
  document.querySelector('#user-name').textContent = d.user.name.replace('DIPAC ', '');
  document.querySelector('#revenue').textContent = rupiah(d.totals.revenue);
  document.querySelector('#profit').textContent = rupiah(d.totals.profit);
  document.querySelector('#pax').textContent = Number(d.totals.pax).toLocaleString('id-ID');
  document.querySelector('#transactions').textContent = Number(d.totals.transactions).toLocaleString('id-ID');
  document.querySelector('#event-rows').innerHTML = d.events.map(e => `<div class="trow" role="row"><span role="cell"><b>${e.name}</b><small>${e.category || ''} · ${e.location}</small></span><span role="cell">${new Date(e.event_date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}</span><span role="cell">${e.pax || '—'}</span><span role="cell">${e.total_revenue ? rupiah(e.total_revenue) : '—'}</span><span role="cell">${e.total_profit ? rupiah(e.total_profit) : '—'}</span></div>`).join('');
  document.querySelector('#insights').innerHTML = d.insights.map((i, n) => `<article><span>0${n + 1}</span><p>${i.recommendation}</p><small>Based on ${i.name}</small></article>`).join('');
}

function renderReports(reports, focusReportId) {
  const count = reports.length;
  const revenue = reports.reduce((sum, report) => sum + Number(report.revenue || 0), 0);
  const collectiveShare = reports.reduce((sum, report) => sum + Number(report.profit || 0), 0);
  const pax = reports.reduce((sum, report) => sum + Number(report.pax || 0), 0);
  const best = reports.slice().sort((a, b) => Number(b.profit || b.revenue || 0) - Number(a.profit || a.revenue || 0))[0];
  document.querySelector('#report-count').textContent = count;
  document.querySelector('#report-revenue').textContent = rupiah(revenue);
  document.querySelector('#report-pax').textContent = count ? Math.round(pax / count).toLocaleString('id-ID') : '0';
  document.querySelector('#best-event').textContent = best ? best.event : '—';
  document.querySelector('#total-collective-share').textContent = rupiah(collectiveShare);
  document.querySelector('#report-list').innerHTML = count ? reports.slice(0, 6).map(r => `<p><b>${r.event}</b><span>${r.file_name} · ${new Date(r.created_at).toLocaleDateString('id-ID')}</span></p>`).join('') : '<p>Belum ada report yang diunggah.</p>';
  document.querySelector('#analysis-report-rows').innerHTML = count ? reports.slice(0, 6).map(r => `<div class="analysis-row" role="row"><span role="cell"><b>${r.event}</b><small>${r.event_date || 'Tanggal tidak tersedia'} · ${r.location || 'Lokasi tidak tersedia'}</small></span><span role="cell">${Number(r.pax || 0).toLocaleString('id-ID')}</span><span role="cell">${rupiah(r.revenue || 0)}</span><span role="cell">${rupiah(r.profit || 0)}</span><span role="cell">${r.insight || 'Analisis tidak tersedia.'}</span></div>`).join('') : '<p class="empty-analysis">Belum ada AI analysis.</p>';

  populateEventSelects(reports, focusReportId);
  loadEventComparison();
}

// =================
// BAR CHART (single-series, vanilla CSS)
// =================
function renderBarChart(containerId, items, labelFn, valueFn, formatFn) {
  const container = document.querySelector(containerId);
  if (!items.length) { container.innerHTML = '<p class="empty-analysis">Belum ada data.</p>'; return; }
  const max = Math.max(...items.map(valueFn), 1);
  container.innerHTML = `<div class="bars">${items.map(item => {
    const value = valueFn(item);
    const pct = Math.max((value / max) * 100, 3);
    return `<div class="bar-col" title="${labelFn(item)}: ${formatFn(value)}">
      <span class="bar-value">${formatFn(value)}</span>
      <div class="bar" style="height:${pct}%"></div>
      <span class="bar-label">${labelFn(item)}</span>
    </div>`;
  }).join('')}</div>`;
}

// =================
// EVENT ANALYSIS (per report)
// =================
function populateEventSelects(reports, focusReportId) {
  const options = reports.length
    ? reports.map(r => `<option value="${r.id}">${r.event} · ${new Date(r.created_at).toLocaleDateString('id-ID')}</option>`).join('')
    : '<option value="">— Belum ada report —</option>';
  const analysisSelect = document.querySelector('#analysis-select');
  const executiveSelect = document.querySelector('#executive-select');
  const prevAnalysis = analysisSelect.value;
  const prevExecutive = executiveSelect.value;
  analysisSelect.innerHTML = options;
  executiveSelect.innerHTML = options;
  if (!reports.length) {
    document.querySelector('#analysis-empty').hidden = false;
    document.querySelector('#analysis-content').hidden = true;
    document.querySelector('#executive-empty').hidden = false;
    document.querySelector('#executive-content').hidden = true;
    return;
  }
  // A just-uploaded report (focusReportId) always wins; otherwise keep
  // whatever the user had selected; fall back to the newest report.
  const pick = prevId => {
    if (focusReportId && reports.some(r => String(r.id) === String(focusReportId))) return focusReportId;
    if (reports.some(r => String(r.id) === prevId)) return prevId;
    return reports[0].id;
  };
  const analysisId = pick(prevAnalysis);
  const executiveId = pick(prevExecutive);
  analysisSelect.value = analysisId;
  executiveSelect.value = executiveId;
  loadEventAnalysis(analysisId);
  loadExecutiveReport(executiveId);
}

async function loadEventAnalysis(reportId) {
  if (!reportId) return;
  document.querySelector('#analysis-empty').hidden = true;
  document.querySelector('#analysis-content').hidden = false;
  try {
    const res = await fetch(`/api/event-analysis?report_id=${reportId}`);
    if (!res.ok) throw new Error('Gagal memuat analisis event');
    const data = await res.json();
    const m = data.metrics;
    document.querySelector('#an-title').textContent = `${data.report.event_name}${data.report.event_date ? ' · ' + data.report.event_date : ''}${data.report.location ? ' · ' + data.report.location : ''}`;
    document.querySelector('#an-spending').textContent = rupiah(m.customer_spending);
    document.querySelector('#an-income').textContent = rupiah(m.collective_income);
    document.querySelector('#an-bottles').textContent = `${Number(m.bottle_sold).toLocaleString('id-ID')} Bottle`;
    document.querySelector('#an-avg').textContent = rupiah(m.average_spending);
    document.querySelector('#an-profit').textContent = rupiah(m.profit_contribution);
    document.querySelector('#an-commission').textContent = `${m.commission_rate}%`;

    const rows = data.transactions;
    document.querySelector('#an-transaction-rows').innerHTML = rows.length
      ? rows.map(t => `<div class="trow" role="row"><span role="cell"><b>${t.menu}</b></span><span role="cell">${t.category}</span><span role="cell">${t.qty}</span><span role="cell">${rupiah(t.customer_price)}</span><span role="cell">${rupiah(t.customer_revenue)}</span><span role="cell">${rupiah(t.collective_share)}</span><span role="cell">${t.commission_pct}%</span><span role="cell">${rupiah(t.profit)}</span></div>`).join('')
      : '<p class="empty-analysis">Tidak ada rincian transaksi untuk report ini.</p>';

    renderBarChart('#an-chart', rows, t => t.menu, t => t.customer_revenue, rupiah);
  } catch (error) {
    document.querySelector('#analysis-content').innerHTML = `<p class="empty-analysis">${error.message}</p>`;
  }
}

// =================
// EVENT COMPARISON
// =================
async function loadEventComparison() {
  try {
    const res = await fetch('/api/event-comparison');
    if (!res.ok) throw new Error('Gagal memuat perbandingan event');
    const data = await res.json();
    if (!data.events.length) {
      document.querySelector('#comparison-empty').hidden = false;
      document.querySelector('#comparison-content').hidden = true;
      return;
    }
    document.querySelector('#comparison-empty').hidden = true;
    document.querySelector('#comparison-content').hidden = false;

    document.querySelector('#cmp-spending').textContent = rupiah(data.totals.total_customer_spending);
    document.querySelector('#cmp-income').textContent = rupiah(data.totals.total_collective_income);
    document.querySelector('#cmp-commission').textContent = `${data.totals.average_commission}%`;
    document.querySelector('#cmp-best').textContent = data.totals.best_event || '—';

    document.querySelector('#cmp-rows').innerHTML = data.events.map(e => {
      const commission = e.revenue ? Math.round((e.profit / e.revenue) * 100 * 100) / 100 : 0;
      return `<div class="trow" role="row"><span role="cell"><b>${e.event_name}</b><small>${e.location || ''}</small></span><span role="cell">${rupiah(e.revenue || 0)}</span><span role="cell">${rupiah(e.profit || 0)}</span><span role="cell">${rupiah(e.profit || 0)}</span><span role="cell">${commission}%</span></div>`;
    }).join('');

    renderBarChart('#cmp-chart', data.events, e => e.event_name, e => e.revenue || 0, rupiah);
  } catch (error) {
    document.querySelector('#comparison-content').innerHTML = `<p class="empty-analysis">${error.message}</p>`;
  }
}

// =================
// EXECUTIVE REPORT
// =================
async function loadExecutiveReport(reportId) {
  if (!reportId) return;
  document.querySelector('#executive-empty').hidden = true;
  document.querySelector('#executive-content').hidden = false;
  try {
    const res = await fetch(`/api/event-analysis?report_id=${reportId}`);
    if (!res.ok) throw new Error('Gagal memuat executive report');
    const data = await res.json();
    const r = data.report;
    const m = data.metrics;
    const best = data.transactions.slice().sort((a, b) => b.collective_share - a.collective_share)[0];

    document.querySelector('#ex-title').textContent = r.event_name;
    document.querySelector('#ex-spending').textContent = rupiah(m.customer_spending);
    document.querySelector('#ex-income').textContent = rupiah(m.collective_income);
    document.querySelector('#ex-profit').textContent = rupiah(m.profit_contribution);
    document.querySelector('#ex-commission').textContent = `${m.commission_rate}%`;
    document.querySelector('#ex-best-menu').textContent = best ? best.menu : '—';

    const recommendations = r.insight_list && r.insight_list.length ? r.insight_list : [r.analysis];
    document.querySelector('#ex-recommendations').innerHTML = recommendations.map(rec => `<li>${rec}</li>`).join('');

    document.querySelector('#ex-transaction-rows').innerHTML = data.transactions.length
      ? data.transactions.map(t => `<div class="trow" role="row"><span role="cell"><b>${t.menu}</b></span><span role="cell">${t.category}</span><span role="cell">${t.qty}</span><span role="cell">${rupiah(t.customer_revenue)}</span><span role="cell">${rupiah(t.profit)}</span></div>`).join('')
      : '<p class="empty-analysis">Tidak ada rincian transaksi untuk report ini.</p>';
  } catch (error) {
    document.querySelector('#executive-content').innerHTML = `<p class="empty-analysis">${error.message}</p>`;
  }
}

document.querySelector('#analysis-select').addEventListener('change', e => loadEventAnalysis(e.target.value));
document.querySelector('#executive-select').addEventListener('change', e => loadExecutiveReport(e.target.value));

async function loadDashboard(focusReportId) {
  if (window.location.port === '5500') {
    if (sessionStorage.getItem('dipac_static_session') !== '1') return window.location.assign('index.html?login=required');
    renderDashboard(staticDashboard);
    renderReports([]);
    document.querySelector('#report-note').textContent = 'Import PDF membutuhkan server Python. Jalankan python3 app.py lalu buka http://localhost:8000.';
    return;
  }
  try {
    const res = await fetch('/api/dashboard');
    if (!res.ok) throw new Error('Unauthorized');
    const dashboard = await res.json();
    const reportResponse = await fetch('/api/reports');
    if (!reportResponse.ok) throw new Error('Reports unavailable');
    renderDashboard(dashboard);
    renderReports(await reportResponse.json(), focusReportId);
  } catch { window.location.assign('/?login=required'); }
}

document.querySelector('#report-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const note = document.querySelector('#report-note');
  if (window.location.port === '5500') { note.textContent = 'Import PDF hanya aktif saat aplikasi dijalankan dengan python3 app.py.'; return; }
  const button = form.querySelector('button');
  button.disabled = true; button.textContent = 'Uploading…'; note.textContent = 'Uploading...';
  try {
    await new Promise(resolve => setTimeout(resolve, 150));
    note.textContent = 'Extracting PDF...';
    const response = await fetch('/api/upload-report', { method: 'POST', body: new FormData(form) });
    note.textContent = 'Analyzing data...';
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Report tidak dapat diproses.');
    const a = result.analysis;
    note.textContent = `Completed ✓ Event analyzed successfully. Revenue ${rupiah(a.revenue)}, profit ${rupiah(a.profit)}, pax ${a.pax}.`;
    form.reset();
    await loadDashboard(a.report_id);
  } catch (error) { note.textContent = error.message || 'Terjadi kendala saat membaca report.'; }
  finally { button.disabled = false; button.textContent = 'Analyze report ↗'; }
});

document.querySelector('#password-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const note = document.querySelector('#password-note');
  const button = form.querySelector('button');
  const currentPassword = form.elements.current_password.value;
  const newPassword = form.elements.new_password.value;
  const confirmPassword = form.elements.confirm_password.value;

  if (newPassword !== confirmPassword) {
    note.textContent = 'Konfirmasi password baru tidak cocok.';
    return;
  }

  button.disabled = true;
  note.textContent = 'Updating...';

  try {
    const response = await fetch('/api/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Password gagal diupdate.');
    note.textContent = 'Password berhasil diganti ✓';
    form.reset();
  } catch (error) {
    note.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

document.querySelector('#logout').onclick = async () => {
  if (window.location.port === '5500') { sessionStorage.removeItem('dipac_static_session'); return window.location.assign('index.html'); }
  await fetch('/api/logout', { method: 'POST' }); window.location.assign('/');
};
document.querySelector('#export').onclick = () => window.print();
loadDashboard();

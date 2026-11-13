const money = value => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(value || 0);
const compactNumber = value => new Intl.NumberFormat('vi-VN', { notation: 'compact', maximumFractionDigits: 1 }).format(value || 0);
const palette = ['#087568', '#9674DB', '#E06480', '#387F9B', '#A16207', '#6553A4', '#237A50', '#5F6F85'];
const SVG_NS = 'http://www.w3.org/2000/svg';
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));

const table = (rows, columns) => rows.length
  ? `<div class="table-responsive"><table class="table table-sm"><thead><tr>${columns.map(c => `<th>${escapeHtml(c[0])}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${columns.map(c => `<td>${escapeHtml(c[2] ? c[2](r[c[1]]) : r[c[1]])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`
  : '<p class="text-secondary mb-0">Không có dữ liệu phù hợp</p>';

function svgNode(name, attributes = {}, text = '') {
  const node = document.createElementNS(SVG_NS, name);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
  if (text !== '') node.textContent = text;
  return node;
}

function createSvg(width, height) {
  return svgNode('svg', { viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: 'xMidYMid meet', 'aria-hidden': 'true' });
}

function emptyChart(host) {
  host.innerHTML = '<div class="chart-empty">Không có dữ liệu phù hợp</div>';
}

function renderDonut(hostId, rows, labelOf, valueOf, centerLabel) {
  const host = document.getElementById(hostId);
  const values = rows.map(valueOf);
  const total = values.reduce((sum, value) => sum + Number(value || 0), 0);
  if (!rows.length || total <= 0) return emptyChart(host);

  const layout = document.createElement('div'); layout.className = 'donut-layout';
  const svg = createSvg(260, 260); const radius = 82; const circumference = 2 * Math.PI * radius;
  svg.appendChild(svgNode('circle', { cx: 130, cy: 130, r: radius, fill: 'none', stroke: '#e8edf3', 'stroke-width': 34 }));
  let offset = 0;
  rows.forEach((row, index) => {
    const value = Number(valueOf(row) || 0); const length = value / total * circumference;
    svg.appendChild(svgNode('circle', { cx: 130, cy: 130, r: radius, fill: 'none', stroke: palette[index % palette.length], 'stroke-width': 34, 'stroke-dasharray': `${length} ${circumference - length}`, 'stroke-dashoffset': -offset, transform: 'rotate(-90 130 130)' }));
    svg.lastElementChild.appendChild(svgNode('title', {}, `${labelOf(row)}: ${value}`));
    offset += length;
  });
  svg.appendChild(svgNode('text', { x: 130, y: 124, 'text-anchor': 'middle', fill: '#667085', 'font-size': 13 }, centerLabel));
  svg.appendChild(svgNode('text', { x: 130, y: 149, 'text-anchor': 'middle', fill: '#243047', 'font-size': 24, 'font-weight': 700 }, total));

  const legend = document.createElement('ul'); legend.className = 'chart-legend';
  rows.forEach((row, index) => {
    const item = document.createElement('li'); const color = document.createElement('span'); const label = document.createElement('span'); const value = document.createElement('strong');
    color.style.background = palette[index % palette.length]; label.textContent = labelOf(row); value.textContent = valueOf(row); item.append(color, label, value); legend.appendChild(item);
  });
  layout.append(svg, legend); host.replaceChildren(layout);
}

function renderHorizontalBars(hostId, rows, labelOf, valueOf, maximum = null) {
  const host = document.getElementById(hostId); if (!rows.length) return emptyChart(host);
  const width = Math.max(host.clientWidth, 280), left = width < 450 ? 110 : 210, right = 40, rowHeight = 38, top = 28, height = Math.max(230, rows.length * rowHeight + 55);
  const labelLimit = width < 450 ? 13 : 26;
  const plotWidth = width - left - right; const max = maximum || Math.max(...rows.map(valueOf), 1); const svg = createSvg(width, height);
  for (let tick = 0; tick <= 5; tick++) {
    const x = left + plotWidth * tick / 5;
    svg.appendChild(svgNode('line', { x1: x, y1: 12, x2: x, y2: height - 26, stroke: '#e8edf3', 'stroke-width': 1 }));
    svg.appendChild(svgNode('text', { x, y: height - 8, 'text-anchor': 'middle', fill: '#5F6F85', 'font-size': 11 }, (max * tick / 5).toFixed(max <= 5 ? 1 : 0)));
  }
  rows.forEach((row, index) => {
    const y = top + index * rowHeight; const label = String(labelOf(row)); const value = Number(valueOf(row) || 0); const barWidth = Math.max(2, value / max * plotWidth);
    svg.appendChild(svgNode('text', { x: left - 12, y: y + 15, 'text-anchor': 'end', fill: '#344054', 'font-size': 12 }, label.length > labelLimit ? `${label.slice(0, labelLimit - 1)}…` : label));
    svg.appendChild(svgNode('rect', { x: left, y, width: barWidth, height: 21, rx: 5, fill: palette[index % palette.length] }));
    svg.lastElementChild.appendChild(svgNode('title', {}, `${label}: ${value}`));
    svg.appendChild(svgNode('text', { x: Math.min(left + barWidth + 7, width - 25), y: y + 15, fill: '#344054', 'font-size': 11, 'font-weight': 700 }, value.toFixed(max <= 5 ? 1 : 0)));
  });
  host.replaceChildren(svg);
  host.classList.add('chart-scroll');
  host.tabIndex = 0;
  host.setAttribute('role', 'region');
  svg.style.minWidth = `${width}px`;
}

function renderVerticalBars(hostId, rows, labelOf, valueOf) {
  const host = document.getElementById(hostId); if (!rows.length) return emptyChart(host);
  const width = Math.max(host.clientWidth, rows.length * 90, 440), height = 360, left = 72, right = 20, top = 20, bottom = 82, plotHeight = height - top - bottom, plotWidth = width - left - right;
  const max = Math.max(...rows.map(valueOf), 1); const step = plotWidth / rows.length; const svg = createSvg(width, height);
  for (let tick = 0; tick <= 4; tick++) {
    const y = top + plotHeight - plotHeight * tick / 4;
    svg.appendChild(svgNode('line', { x1: left, y1: y, x2: width - right, y2: y, stroke: '#e8edf3' }));
    svg.appendChild(svgNode('text', { x: left - 10, y: y + 4, 'text-anchor': 'end', fill: '#5F6F85', 'font-size': 11 }, compactNumber(max * tick / 4)));
  }
  rows.forEach((row, index) => {
    const value = Number(valueOf(row) || 0), barHeight = value / max * plotHeight, barWidth = Math.min(52, step * .62), x = left + step * index + (step - barWidth) / 2, y = top + plotHeight - barHeight;
    svg.appendChild(svgNode('rect', { x, y, width: barWidth, height: barHeight, rx: 5, fill: palette[index % palette.length] }));
    svg.lastElementChild.appendChild(svgNode('title', {}, `${labelOf(row)}: ${money(value)}`));
    const label = String(labelOf(row)); const text = svgNode('text', { x: x + barWidth / 2, y: height - 62, 'text-anchor': 'end', fill: '#475467', 'font-size': 12, transform: `rotate(-30 ${x + barWidth / 2} ${height - 62})` }, label.length > 20 ? `${label.slice(0, 19)}…` : label); svg.appendChild(text);
  });
  host.replaceChildren(svg);
  host.classList.add('chart-scroll');
  host.tabIndex = 0;
  host.setAttribute('role', 'region');
  svg.style.minWidth = `${width}px`;
}

function renderLine(hostId, rows, labelOf, valueOf) {
  const host = document.getElementById(hostId); if (!rows.length) return emptyChart(host);
  const width = Math.max(host.clientWidth, rows.length * 72, 360), height = 320, left = 70, right = 25, top = 25, bottom = 52, plotWidth = width - left - right, plotHeight = height - top - bottom;
  const max = Math.max(...rows.map(valueOf), 1), svg = createSvg(width, height);
  for (let tick = 0; tick <= 4; tick++) {
    const y = top + plotHeight - plotHeight * tick / 4;
    svg.appendChild(svgNode('line', { x1: left, y1: y, x2: width - right, y2: y, stroke: '#e8edf3' }));
    svg.appendChild(svgNode('text', { x: left - 10, y: y + 4, 'text-anchor': 'end', fill: '#5F6F85', 'font-size': 11 }, compactNumber(max * tick / 4)));
  }
  const points = rows.map((row, index) => ({ x: left + (rows.length === 1 ? plotWidth / 2 : plotWidth * index / (rows.length - 1)), y: top + plotHeight - Number(valueOf(row) || 0) / max * plotHeight, row }));
  const line = points.map(point => `${point.x},${point.y}`).join(' ');
  svg.appendChild(svgNode('polyline', { points: line, fill: 'none', stroke: '#087568', 'stroke-width': 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
  points.forEach(point => { svg.appendChild(svgNode('circle', { cx: point.x, cy: point.y, r: 5, fill: '#fff', stroke: '#087568', 'stroke-width': 3 })); svg.appendChild(svgNode('text', { x: point.x, y: height - 18, 'text-anchor': 'middle', fill: '#475467', 'font-size': 11 }, labelOf(point.row))); svg.lastElementChild.appendChild(svgNode('title', {}, `${labelOf(point.row)}: ${money(valueOf(point.row))}`)); });
  host.replaceChildren(svg);
  host.classList.add('chart-scroll');
  host.tabIndex = 0;
  host.setAttribute('role', 'region');
  svg.style.minWidth = `${width}px`;
}

function hideFallback(id) {
  // Keep exact values and complete labels available to keyboard/screen-reader users.
  const host = document.getElementById(id);
  const details = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = 'Xem bảng dữ liệu';
  details.append(summary, ...host.childNodes);
  host.replaceChildren(details);
}
function renderSection(label, hostId, callback) {
  try { callback(); }
  catch (error) {
    console.error(`Lỗi biểu đồ ${label}:`, error);
    const host = document.getElementById(hostId);
    if (host) { host.innerHTML = ''; const message = document.createElement('div'); message.className = 'chart-empty'; message.setAttribute('role', 'alert'); message.textContent = `Không tải được ${label}. `; const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'btn btn-outline-secondary btn-sm'; retry.textContent = 'Thử lại'; retry.addEventListener('click', () => location.reload()); message.appendChild(retry); host.appendChild(message); }
  }
}

document.querySelectorAll('.svg-chart-host').forEach(host => {
  host.setAttribute('aria-busy', 'true');
  const skeleton = document.createElement('div'); skeleton.className = 'chart-skeleton'; skeleton.setAttribute('aria-hidden', 'true'); host.appendChild(skeleton);
});

Promise.all(['/api/dashboard/summary', '/api/dashboard/ratings', '/api/dashboard/promotions', '/api/dashboard/sales'].map(url => fetch(url).then(response => {
  if (!response.ok) throw new Error('Không tải được dữ liệu'); return response.json();
}).catch(() => ({ data: {}, uiError: true })))).then(([summary, ratings, promotions, sales]) => {
  const s = summary.data;
  if (summary.uiError) {
    document.querySelector('#summary').innerHTML = '<div class="col-12"><div class="alert alert-danger" role="alert">Không tải được số liệu tổng quan. <button type="button" class="btn btn-outline-danger btn-sm" data-dashboard-retry>Thử lại</button></div></div>';
  } else {
  document.querySelector('#summary').innerHTML = [['Sản phẩm hoạt động', s.activeProducts], ['Khuyến mãi hoạt động', s.activePromotions], ['Điểm trung bình', `${String(s.averageRating).replace('.', ',')}/5`], ['Doanh thu', money(s.revenue)], ['Tiền đã giảm', money(s.discount)]].map(item => `<div class="col"><div class="card kpi-card h-100"><div class="card-body"><div class="kpi-label">${item[0]}</div><div class="kpi-value">${escapeHtml(item[1])}</div></div></div></div>`).join('');
  }

  renderSection('phân bố đánh giá', 'ratingDistributionChart', () => {
    if (ratings.uiError) throw new Error('API unavailable');
    const rows = ratings.data.NC03 || [];
    document.querySelector('#ratingDistributionFallback').innerHTML = table(rows, [['Mức sao', 'rating'], ['Số đánh giá', 'totalReviews']]);
    renderDonut('ratingDistributionChart', rows, row => `${row.rating} sao`, row => row.totalReviews, 'Đánh giá'); if (rows.length) hideFallback('ratingDistributionFallback');
  });

  renderSection('điểm trung bình sản phẩm', 'productRatingChart', () => {
    if (ratings.uiError) throw new Error('API unavailable');
    const rows = (ratings.data.NC09 || []).slice(0, 10);
    document.querySelector('#ratings').innerHTML = table(rows, [['Sản phẩm', 'productName'], ['Số đánh giá', 'reviewCount'], ['Điểm TB', 'avgRating']]);
    renderHorizontalBars('productRatingChart', rows, row => row.productName, row => row.avgRating, 5); if (rows.length) hideFallback('ratings');
  });

  renderSection('mức sử dụng khuyến mãi', 'promotionUsageChart', () => {
    if (promotions.uiError) throw new Error('API unavailable');
    const rows = promotions.data.NC07 || [];
    document.querySelector('#promotions').innerHTML = table(rows, [['Mã', 'promoCode'], ['Lượt dùng', 'usageCount'], ['Tiền giảm', 'totalDiscount', money]]);
    renderDonut('promotionUsageChart', rows, row => row.promoCode, row => row.usageCount, 'Lượt dùng'); if (rows.length) hideFallback('promotions');
  });

  renderSection('doanh thu theo thời gian', 'revenueTimelineChart', () => {
    if (sales.uiError) throw new Error('API unavailable');
    const rows = sales.data.NC08 || [];
    const period = row => `${String(row.month).padStart(2, '0')}/${row.year}`;
    document.querySelector('#timelineFallback').innerHTML = table(rows.map(row => ({ period: period(row), revenue: row.revenue })), [['Tháng', 'period'], ['Doanh thu', 'revenue', money]]);
    renderLine('revenueTimelineChart', rows, period, row => row.revenue); if (rows.length) hideFallback('timelineFallback');
  });

  renderSection('doanh thu sản phẩm', 'productSalesChart', () => {
    if (sales.uiError) throw new Error('API unavailable');
    const rows = (sales.data.NC05 || []).slice(0, 10);
    document.querySelector('#sales').innerHTML = table(rows, [['Sản phẩm', 'productName'], ['Đã bán', 'quantitySold'], ['Doanh thu', 'revenueBeforeDiscount', money]]);
    renderVerticalBars('productSalesChart', rows, row => row.productName, row => row.revenueBeforeDiscount); if (rows.length) hideFallback('sales');
  });
}).catch(error => {
  console.error('Lỗi tải API dashboard:', error);
  const summary = document.querySelector('#summary'); summary.innerHTML = '';
  const alert = document.createElement('div'); alert.className = 'col-12'; alert.innerHTML = '<div class="alert alert-danger mb-0">Không kết nối được API thống kê. Vui lòng tải lại trang.</div>'; summary.appendChild(alert);
})
// Remove loading semantics after every request has settled, including partial failure.
.finally(() => {
  document.querySelectorAll('.svg-chart-host, #summary').forEach(host => host.removeAttribute('aria-busy'));
  document.querySelector('[data-dashboard-retry]')?.addEventListener('click', () => location.reload());
});

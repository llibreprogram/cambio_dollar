// Initial theme setting (moved from base.html)
(function () {
  try {
    const storedTheme = window.localStorage.getItem("cambio-theme");
    const prefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
    const initial = storedTheme || (prefersLight ? "light" : "dark");
    document.documentElement.setAttribute("data-theme", initial);
  } catch (error) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
})();

// Variables globales del estado de la app
let currentChartPeriod = 24;
let isLiveMode = false;
let liveUpdateInterval = null;
let trendChart = null;
let lastUpdateTimestamp = new Date();
let eventSource = null;

// Funciones de formateo y utilidad
function fmtNumber(value, decimals = 2) {
  if (value === null || value === undefined || isNaN(value)) return '—';
  return Number(value).toLocaleString('es-DO', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function shortText(text, maxLength) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function parseDate(dateStr) {
  return dateStr ? new Date(dateStr) : new Date();
}

function updateTimeAgo(timestamp) {
  if (!timestamp) return '—';
  const now = new Date();
  const diff = now - timestamp;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (seconds < 10) return 'ahora mismo';
  if (seconds < 60) return `hace ${seconds}s`;
  if (minutes < 60) return `hace ${minutes}m`;
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${days}d`;
}

// Sistema de Toasts Premium
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  else if (type === 'warning') icon = '⚠️';
  else if (type === 'error') icon = '❌';

  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  // Auto destruir
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    toast.style.transition = 'opacity 0.3s, transform 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Animación de actualización flash
function animateValueChange(element, newValue, isNumeric = true, prefix = '', suffix = '') {
  if (!element) return;
  const oldText = element.textContent.trim();
  const cleanNewVal = isNumeric ? fmtNumber(newValue) : newValue;
  const newText = `${prefix}${cleanNewVal}${suffix}`;

  if (oldText !== newText && oldText !== '—') {
    element.textContent = newText;
    
    // Comparación numérica para color de flash
    if (isNumeric) {
      const oldNum = parseFloat(oldText.replace(/[^\d.-]/g, ''));
      const newNum = parseFloat(newValue);
      if (!isNaN(oldNum) && !isNaN(newNum)) {
        if (newNum > oldNum) {
          element.classList.remove('flash-green', 'flash-red');
          void element.offsetWidth; // Trigger reflow
          element.classList.add('flash-green');
        } else if (newNum < oldNum) {
          element.classList.remove('flash-green', 'flash-red');
          void element.offsetWidth;
          element.classList.add('flash-red');
        }
      }
    } else {
      element.classList.remove('flash-green');
      void element.offsetWidth;
      element.classList.add('flash-green');
    }
  } else {
    element.textContent = newText;
  }
}

// ============================================================================ 
// Real-Time Server-Sent Events (SSE)
// ============================================================================ 
function initSSE() {
  if (eventSource) {
    eventSource.close();
  }

  console.log("🔌 Iniciando conexión SSE en /api/events...");
  eventSource = new EventSource('/api/events');

  eventSource.onmessage = function (event) {
    console.log("✉️ SSE evento recibido:", event.data);
    if (event.data === "refresh") {
      showToast("Actualización de mercado en tiempo real recibida", "success");
      refreshDashboardData(true);
    }
  };

  eventSource.onerror = function (error) {
    console.warn("⚠️ Conexión SSE interrumpida. Reintentando...", error);
    // reconecta automáticamente a través de la API del navegador
  };
}

// ============================================================================ 
// Refresco Dinámico de Datos (SPA sin recarga)
// ============================================================================ 
async function refreshDashboardData(updateChart = false) {
  try {
    // 1. Obtener Consenso
    const resConsensus = await fetch('/api/consensus');
    if (!resConsensus.ok) throw new Error("Error obteniendo consenso");
    const consensus = await resConsensus.json();
    lastUpdateTimestamp = consensus.timestamp ? new Date(consensus.timestamp) : new Date();

    // Actualizar tiempo ago inmediatamente
    const timeAgoElement = document.getElementById('time-ago');
    if (timeAgoElement) timeAgoElement.textContent = updateTimeAgo(lastUpdateTimestamp);

    // Actualizar fichas de consenso del Hero
    const midChips = document.querySelectorAll('.chip-positive');
    midChips.forEach(chip => {
      if (chip.textContent.includes('Mid')) {
        chip.textContent = `📊 Mid ${fmtNumber(consensus.mid_rate)} DOP`;
      }
    });

    const heroSummary = document.querySelector('.hero-summary');
    if (heroSummary && consensus) {
      const activeCount = window.GLOBAL_PROVIDER_STATUS_JSON.filter(p => p.enabled).length;
      heroSummary.textContent = `Seguimiento en tiempo real al consenso del mercado: mid ${fmtNumber(consensus.mid_rate)} DOP, divergencia ${fmtNumber(consensus.divergence_range, 3)} y ${activeCount}/${window.GLOBAL_PROVIDER_STATUS_JSON.length} proveedores activos.`;
    }

    // Actualizar tarjetas dinámicas (Consenso actual)
    const consensusCard = document.querySelector('.card:nth-child(1)');
    if (consensusCard && consensus) {
      const vals = consensusCard.querySelectorAll('.stat-value');
      if (vals.length >= 3) {
        animateValueChange(vals[0], consensus.buy_rate);
        animateValueChange(vals[1], consensus.sell_rate);
        animateValueChange(vals[2], consensus.weighted_mid_rate);
      }
      const consensusTime = consensusCard.querySelector('.timestamp');
      if (consensusTime) {
        consensusTime.textContent = new Date(consensus.timestamp).toLocaleString();
      }
      const divStrong = consensusCard.querySelector('.stat-foot strong');
      if (divStrong) {
        divStrong.textContent = fmtNumber(consensus.divergence_range, 3);
      }
    }

    // 2. Obtener Recomendación IA
    const resRec = await fetch('/api/recommendation');
    if (resRec.ok) {
      const rec = await resRec.json();
      
      // Actualizar tarjeta del Hero
      const heroStats = document.querySelector('.hero-stats');
      if (heroStats) {
        const statCards = heroStats.querySelectorAll('.hero-stat-card');
        if (statCards.length >= 3) {
          // Acción sugerida
          const valAction = statCards[0].querySelector('.hero-stat-value');
          if (valAction) valAction.textContent = rec.action.toUpperCase();
          const metaAction = statCards[0].querySelector('.hero-stat-meta');
          if (metaAction) metaAction.textContent = `Confianza ${fmtNumber(rec.score * 100, 0)}%`;

          // Ganancia esperada
          const valProfit = statCards[1].querySelector('.hero-stat-value');
          if (valProfit) animateValueChange(valProfit, rec.expected_profit, true, '', ' DOP');
          const metaProfit = statCards[1].querySelector('.hero-stat-meta');
          if (metaProfit) metaProfit.textContent = `Ventaja ${fmtNumber(rec.spread_advantage, 3)}`;
        }
      }

      // Actualizar Tarjeta de Recomendación Activa
      const recCard = document.querySelector('.card.success');
      if (recCard) {
        const timestampEl = recCard.querySelector('.timestamp');
        if (timestampEl) timestampEl.textContent = new Date(rec.generated_at).toLocaleString();

        const vals = recCard.querySelectorAll('.stat-value');
        if (vals.length >= 3) {
          vals[0].textContent = rec.action.toUpperCase();
          vals[1].textContent = `${fmtNumber(rec.score * 100, 0)}%`;
          animateValueChange(vals[2], rec.expected_profit, true, '', ' DOP');
        }

        const bullets = recCard.querySelectorAll('.mini-list li strong');
        if (bullets.length >= 3) {
          bullets[0].textContent = fmtNumber(rec.suggested_buy_rate);
          bullets[1].textContent = fmtNumber(rec.suggested_sell_rate);
          bullets[2].textContent = fmtNumber(rec.spread_advantage, 3);
        }

        const reasonText = recCard.querySelector('.reason');
        if (reasonText) reasonText.textContent = rec.reason;
      }
    }

    // 3. Obtener Forecast de Cierre
    const resForecast = await fetch('/api/forecast');
    if (resForecast.ok) {
      const fc = await resForecast.json();
      const forecastCard = document.querySelector('.card.forecast');
      if (forecastCard) {
        const timestampEl = forecastCard.querySelector('.timestamp');
        if (timestampEl) timestampEl.textContent = new Date(fc.generated_at).toLocaleString();

        const vals = forecastCard.querySelectorAll('.stat-value');
        if (vals.length >= 3) {
          animateValueChange(vals[0], fc.expected_profit_end_day);
          animateValueChange(vals[1], fc.best_case);
          animateValueChange(vals[2], fc.worst_case);
        }

        const foot = forecastCard.querySelector('.stat-foot');
        if (foot) {
          foot.textContent = `Intervalo ±${fmtNumber(fc.confidence_interval)} DOP · ${fc.details}`;
        }
      }
    }

    // 4. Refrescar listas e historias
    await refreshTables();

    // 5. Refrescar calculadora rápida con datos nuevos
    const calcAmount = document.getElementById('calc-amount');
    if (calcAmount && calcAmount.value) {
      updateCalculator(parseFloat(calcAmount.value), consensus);
    }

    // 6. Actualizar gráfico si es necesario
    if (updateChart && trendChart) {
      await renderChart(currentChartPeriod);
    }

  } catch (error) {
    console.error("Error actualizando dashboard:", error);
  }
}

// Refrescar tablas dinámicas (trades, snapshots, providers)
async function refreshTables() {
  try {
    // 1. Tabla de Historial de Operaciones
    const resTrades = await fetch('/api/history?limit=8', { method: 'POST' });
    if (resTrades.ok) {
      const trades = await resTrades.json();
      const tbody = document.getElementById('trade-history-tbody');
      if (tbody) {
        tbody.innerHTML = '';
        if (trades.length === 0) {
          tbody.innerHTML = `<tr><td colspan="6" class="empty-state">Sin operaciones registradas.</td></tr>`;
        } else {
          trades.forEach(trade => {
            const date = new Date(trade.timestamp);
            const time = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            const profitClass = trade.profit_dop >= 0 ? 'positive' : 'negative';
            const tr = document.createElement('tr');
            tr.setAttribute('data-trade-id', trade.id || '');
            tr.innerHTML = `
              <td>${time}</td>
              <td>${trade.action.toUpperCase()}</td>
              <td>${fmtNumber(trade.usd_amount)}</td>
              <td>${fmtNumber(trade.rate)}</td>
              <td class="${profitClass}">${fmtNumber(trade.profit_dop)}</td>
              <td>
                <button class="btn-edit-trade" data-trade-id="${trade.id}">✏️</button>
                <button class="btn-delete-trade" data-trade-id="${trade.id}">🗑️</button>
              </td>
            `;
            tbody.appendChild(tr);
          });
        }
      }
    }

    // 2. Tabla de Proveedores y Comparación
    const resProviders = await fetch('/api/providers');
    if (resProviders.ok) {
      const providers = await resProviders.json();
      window.GLOBAL_PROVIDER_STATUS_JSON = providers; // Actualizar cache de comparación
      const tbody = document.getElementById('provider-table-body');
      if (tbody) {
        tbody.innerHTML = '';
        providers.forEach(p => {
          const enabledClass = p.enabled ? 'tag-on' : 'tag-off';
          const enabledText = p.enabled ? 'Sí' : 'No';
          const originHtml = p.aggregated ? `<span class="tag tag-aggregated">${p.origin || 'Agregado'}</span>` : (p.origin || 'Directo');
          const lastUpdate = p.last_timestamp ? new Date(p.last_timestamp).toLocaleString() : '—';
          
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${p.name}</td>
            <td><span class="tag ${enabledClass}">${enabledText}</span></td>
            <td>${originHtml}</td>
            <td>${fmtNumber(p.buy_rate)}</td>
            <td>${fmtNumber(p.sell_rate)}</td>
            <td>${lastUpdate}</td>
          `;
          tbody.appendChild(tr);
        });
      }
      
      // Actualizar conteo de cobertura
      const total = providers.length;
      const enabled = providers.filter(p => p.enabled).length;
      const pct = total ? Math.round((enabled / total) * 100) : 0;
      
      const coverageChips = document.querySelectorAll('#coverage-chip, #coverage-chip-secondary');
      coverageChips.forEach(chip => {
        chip.textContent = `🔌 ${enabled}/${total} activos (${pct}%)`;
        chip.className = `chip ${pct >= 80 ? 'chip-positive' : (pct >= 50 ? 'chip-neutral' : 'chip-warn')}`;
      });

      // Sincronizar selectores de comparación
      updateComparisonSelects(providers);
    }

    // 3. Tabla de Snapshots Recientes
    const resSnaps = await fetch(`/api/snapshots?minutes=180`);
    if (resSnaps.ok) {
      const snaps = await resSnaps.json();
      const tbody = document.getElementById('recent-snapshots-tbody');
      if (tbody) {
        tbody.innerHTML = '';
        const limitSnaps = snaps.slice(0, 20);
        if (limitSnaps.length === 0) {
          tbody.innerHTML = `<tr><td colspan="4" class="empty-state">Sin lecturas almacenadas.</td></tr>`;
        } else {
          limitSnaps.forEach(s => {
            const date = new Date(s.timestamp);
            const formattedDate = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td>${formattedDate}</td>
              <td>${s.source}</td>
              <td>${fmtNumber(s.buy_rate)}</td>
              <td>${fmtNumber(s.sell_rate)}</td>
            `;
            tbody.appendChild(tr);
          });
        }
      }
    }
  } catch (err) {
    console.error("Error al refrescar tablas:", err);
  }
}

// Sincronizar opciones de proveedores en selectores de comparación
function updateComparisonSelects(providers) {
  const p1 = document.getElementById('provider-1');
  const p2 = document.getElementById('provider-2');
  if (!p1 || !p2) return;

  const val1 = p1.value;
  const val2 = p2.value;

  p1.innerHTML = '<option value="">Seleccionar Proveedor 1</option>';
  p2.innerHTML = '<option value="">Seleccionar Proveedor 2</option>';

  providers.forEach(p => {
    const opt1 = document.createElement('option');
    opt1.value = p.name;
    opt1.textContent = p.name;
    opt1.selected = p.name === val1;
    p1.appendChild(opt1);

    const opt2 = document.createElement('option');
    opt2.value = p.name;
    opt2.textContent = p.name;
    opt2.selected = p.name === val2;
    p2.appendChild(opt2);
  });
}

// ============================================================================ 
// Modal de Operaciones (Creación y Edición)
// ============================================================================ 
const modal = document.getElementById('trade-modal');
const modalTitle = document.getElementById('modal-title');
const modalForm = document.getElementById('modal-trade-form');
const modalTradeId = document.getElementById('modal-trade-id');
const modalAmountInput = document.getElementById('modal-trade-amount');
const modalRateInput = document.getElementById('modal-trade-rate');
const modalFeesInput = document.getElementById('modal-trade-fees');
const modalResult = document.getElementById('modal-trade-result');
const modalSubmitBtn = document.getElementById('modal-submit-btn');

function openTradeModal(tradeData = null) {
  if (!modal) return;

  // Limpiar estados
  modalResult.textContent = '';
  modalResult.className = 'hint';
  modalForm.reset();

  if (tradeData) {
    // Editar
    modalTitle.textContent = `Editar Operación #${tradeData.id}`;
    modalTradeId.value = tradeData.id;
    
    // Marcar acción (buy/sell)
    if (tradeData.action === 'buy') {
      document.getElementById('modal-action-buy').checked = true;
    } else {
      document.getElementById('modal-action-sell').checked = true;
    }

    modalAmountInput.value = tradeData.usd_amount;
    modalRateInput.value = tradeData.rate || '';
    modalFeesInput.value = tradeData.fees !== undefined ? tradeData.fees : '';
    modalSubmitBtn.textContent = 'Guardar Cambios';
  } else {
    // Crear
    modalTitle.textContent = 'Registrar Operación';
    modalTradeId.value = '';
    
    // Pre-poblar acción con recomendación actual si está disponible
    const recAction = document.querySelector('.card.success .stat-value')?.textContent.trim().toLowerCase();
    if (recAction === 'buy') {
      document.getElementById('modal-action-buy').checked = true;
    } else {
      document.getElementById('modal-action-sell').checked = true;
    }

    // Pre-poblar tasa sugerida
    const consensusRate = document.getElementById('calc-amount') ? window.GLOBAL_CONSENSUS_BUY_RATE : null;
    modalRateInput.value = '';
    modalFeesInput.value = '';
    modalSubmitBtn.textContent = 'Guardar Operación';
  }

  modal.style.display = 'flex';
}

function closeTradeModal() {
  if (modal) modal.style.display = 'none';
}

// Configurar listeners del modal
document.addEventListener('DOMContentLoaded', () => {
  const openModalBtn = document.getElementById('open-trade-modal-btn');
  const cancelBtn = document.getElementById('modal-cancel-btn');
  const closeBtn = document.getElementById('modal-close-btn');

  if (openModalBtn) openModalBtn.addEventListener('click', () => openTradeModal());
  if (cancelBtn) cancelBtn.addEventListener('click', closeTradeModal);
  if (closeBtn) closeBtn.addEventListener('click', closeTradeModal);

  // Cerrar modal al hacer clic fuera del card
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeTradeModal();
    });
  }

  // Enviar formulario del modal
  if (modalForm) {
    modalForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const tradeId = modalTradeId.value;
      const isEdit = tradeId !== '';
      
      const action = document.querySelector('input[name="modal-trade-action"]:checked').value;
      const amount = parseFloat(modalAmountInput.value);
      const rateVal = modalRateInput.value;
      const feesVal = modalFeesInput.value;

      if (isNaN(amount) || amount <= 0) {
        modalResult.textContent = '❌ Error: El monto USD debe ser mayor a 0';
        modalResult.className = 'hint status-error';
        return;
      }

      const payload = {
        action: action,
        usd_amount: amount
      };

      if (rateVal && parseFloat(rateVal) > 0) payload.rate = parseFloat(rateVal);
      if (feesVal && parseFloat(feesVal) >= 0) payload.fees = parseFloat(feesVal);

      modalSubmitBtn.disabled = true;
      modalSubmitBtn.textContent = 'Procesando...';

      try {
        const endpoint = isEdit ? `/api/trade/${tradeId}` : '/api/trade';
        const method = isEdit ? 'PUT' : 'POST';

        const response = await fetch(endpoint, {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Error HTTP ${response.status}`);
        }

        showToast(
          isEdit ? `Operación #${tradeId} actualizada exitosamente.` : 'Nueva operación registrada con éxito.',
          'success'
        );
        closeTradeModal();
        
        // Notificar cambio localmente de inmediato si el SSE tarda
        refreshDashboardData();

      } catch (err) {
        console.error(err);
        modalResult.textContent = `❌ Error: ${err.message}`;
        modalResult.className = 'hint status-error';
      } finally {
        modalSubmitBtn.disabled = false;
        modalSubmitBtn.textContent = isEdit ? 'Guardar Cambios' : 'Guardar Operación';
      }
    });
  }
});

// ============================================================================ 
// Gráfico de Tendencia con Banda de Spread (Chart.js 4)
// ============================================================================ 
async function loadChartData(hours = 24) {
  try {
    const minutes = hours * 60;
    const response = await fetch(`/api/snapshots?minutes=${minutes}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('Error cargando datos de gráfico:', error);
    return [];
  }
}

function processChartData(snapshots) {
  if (!snapshots || snapshots.length === 0) {
    return { labels: [], buyRates: [], sellRates: [], rawData: [] };
  }

  // Agrupar por timestamp para promediar lecturas concurrentes
  const grouped = {};
  snapshots.forEach(snap => {
    const timestamp = new Date(snap.timestamp).getTime();
    if (!grouped[timestamp]) {
      grouped[timestamp] = { buy: [], sell: [], timestamp: snap.timestamp };
    }
    grouped[timestamp].buy.push(snap.buy_rate);
    grouped[timestamp].sell.push(snap.sell_rate);
  });

  // Promediar y ordenar cronológicamente
  const processed = Object.values(grouped)
    .map(group => ({
      timestamp: group.timestamp,
      buyRate: group.buy.reduce((a, b) => a + b, 0) / group.buy.length,
      sellRate: group.sell.reduce((a, b) => a + b, 0) / group.sell.length
    }))
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  // Limitar cantidad de puntos visualizados
  const maxPoints = 60;
  const step = Math.ceil(processed.length / maxPoints);
  const reduced = processed.filter((_, index) => index % step === 0);

  return {
    labels: reduced.map(d => {
      const date = new Date(d.timestamp);
      return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    }),
    buyRates: reduced.map(d => d.buyRate),
    sellRates: reduced.map(d => d.sellRate),
    rawData: processed
  };
}

function calculateStats(data) {
  if (!data || data.length === 0) return null;

  const buyRates = data.map(d => d.buyRate);
  const avgBuy = buyRates.reduce((a, b) => a + b, 0) / buyRates.length;
  
  const sellRates = data.map(d => d.sellRate);
  const avgSell = sellRates.reduce((a, b) => a + b, 0) / sellRates.length;

  const variance = buyRates.reduce((sum, rate) => sum + Math.pow(rate - avgBuy, 2), 0) / buyRates.length;
  const volatility = Math.sqrt(variance);

  const quarter = Math.floor(data.length / 4) || 1;
  const firstQuarter = buyRates.slice(0, quarter).reduce((a, b) => a + b, 0) / quarter;
  const lastQuarter = buyRates.slice(-quarter).reduce((a, b) => a + b, 0) / quarter;
  const trend = lastQuarter - firstQuarter;

  return { avgBuy, avgSell, volatility, trend };
}

async function renderChart(hours = 24) {
  const canvasElement = document.getElementById('trend-chart');
  if (!canvasElement || typeof Chart === 'undefined') return;

  try {
    const snapshots = await loadChartData(hours);
    const chartData = processChartData(snapshots);
    const stats = calculateStats(chartData.rawData);

    if (trendChart) {
      trendChart.destroy();
    }

    const ctx = canvasElement.getContext('2d');
    
    // Crear gradientes de fondo premium para las líneas y el sombreado de spread
    const buyGradient = ctx.createLinearGradient(0, 0, 0, 300);
    buyGradient.addColorStop(0, 'rgba(14, 165, 233, 0.22)');
    buyGradient.addColorStop(1, 'rgba(14, 165, 233, 0)');

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(15, 23, 42, 0.05)';
    const textColor = isDark ? '#94a3b8' : '#64748b';

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'Compra (Vender USD)',
            data: chartData.buyRates,
            borderColor: '#0ea5e9', // accent-cyan
            backgroundColor: 'transparent',
            borderWidth: 2.5,
            tension: 0.35,
            pointRadius: 2.5,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: '#0ea5e9',
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2
          },
          {
            label: 'Venta (Comprar USD)',
            data: chartData.sellRates,
            borderColor: '#10b981', // accent-mint
            // fill: 0 rellena el área entre este dataset (indice 1) y el anterior (indice 0)
            fill: 0,
            backgroundColor: isDark ? 'rgba(14, 165, 233, 0.06)' : 'rgba(2, 132, 199, 0.05)',
            borderWidth: 2.5,
            tension: 0.35,
            pointRadius: 2.5,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: '#10b981',
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: textColor,
              font: {
                family: 'Outfit',
                size: 12,
                weight: '600'
              },
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 15
            }
          },
          tooltip: {
            enabled: true,
            backgroundColor: isDark ? 'rgba(13, 20, 37, 0.95)' : 'rgba(255, 255, 255, 0.95)',
            titleColor: isDark ? '#f8fafc' : '#0f172a',
            bodyColor: isDark ? '#f8fafc' : '#0f172a',
            borderColor: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
            borderWidth: 1,
            padding: 12,
            titleFont: { family: 'Outfit', weight: 'bold' },
            bodyFont: { family: 'Outfit' },
            callbacks: {
              label: function (context) {
                return ` ${context.dataset.label}: ${fmtNumber(context.parsed.y)} DOP`;
              },
              afterBody: function(items) {
                if (items.length >= 2) {
                  const buy = items[0].parsed.y;
                  const sell = items[1].parsed.y;
                  const spread = sell - buy;
                  return ` Spread: ${fmtNumber(spread, 3)} DOP`;
                }
                return '';
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: gridColor },
            ticks: {
              color: textColor,
              font: { family: 'Outfit', size: 10 }
            }
          },
          y: {
            grid: { color: gridColor },
            ticks: {
              color: textColor,
              font: { family: 'Outfit', size: 11 },
              callback: function (value) { return value.toFixed(2) + ' DOP'; }
            }
          }
        }
      }
    });

    // Actualizar bloque de estadísticas bajo el gráfico
    if (stats) {
      const avgBuyEl = document.getElementById('chart-avg-buy');
      const avgSellEl = document.getElementById('chart-avg-sell');
      const volatilityEl = document.getElementById('chart-volatility');
      const trendEl = document.getElementById('chart-trend');

      if (avgBuyEl) avgBuyEl.textContent = fmtNumber(stats.avgBuy) + ' DOP';
      if (avgSellEl) avgSellEl.textContent = fmtNumber(stats.avgSell) + ' DOP';

      if (volatilityEl) {
        const volLevel = stats.volatility < 0.1 ? 'Muy Baja' : stats.volatility < 0.3 ? 'Baja' : 'Alta';
        volatilityEl.textContent = `${volLevel} (${fmtNumber(stats.volatility, 3)})`;
      }

      if (trendEl) {
        const isUp = stats.trend > 0.01;
        const isDown = stats.trend < -0.01;
        trendEl.textContent = isUp ? '📈 Alcista' : (isDown ? '📉 Bajista' : '➡️ Estable');
        trendEl.style.color = isUp ? 'var(--positive-color)' : (isDown ? 'var(--accent-rose)' : 'var(--accent-amber)');
      }
    }

  } catch (error) {
    console.error('Error renderizando gráfico:', error);
  }
}

// Configurar listeners del gráfico periodos
document.addEventListener('DOMContentLoaded', () => {
  const periodButtons = document.querySelectorAll('.chart-period-btn');
  periodButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      // Detener LIVE si salimos de ese modo
      if (isLiveMode && !btn.classList.contains('live-btn')) {
        clearInterval(liveUpdateInterval);
        liveUpdateInterval = null;
        isLiveMode = false;
        showToast('Modo LIVE desactivado', 'info');
      }

      periodButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const hours = parseFloat(btn.dataset.hours);
      currentChartPeriod = hours;

      if (btn.classList.contains('live-btn')) {
        isLiveMode = true;
        await renderChart(hours);
        liveUpdateInterval = setInterval(async () => {
          await renderChart(hours);
        }, 15000); // 15 segundos para LIVE real-time
        showToast('Modo LIVE activo (15s update)', 'success');
      } else {
        await renderChart(hours);
      }
    });
  });
});

// ============================================================================ 
// Calculadora Rápida
// ============================================================================ 
function updateCalculator(amount, consensusData = null) {
  const buyEl = document.getElementById('calc-buy');
  const sellEl = document.getElementById('calc-sell');
  const profitEl = document.getElementById('calc-profit');
  if (!buyEl || !sellEl || !profitEl) return;

  if (!amount || amount <= 0) {
    buyEl.textContent = '—';
    sellEl.textContent = '—';
    profitEl.textContent = '—';
    return;
  }

  const buyRate = consensusData ? consensusData.buy_rate : window.GLOBAL_CONSENSUS_BUY_RATE;
  const sellRate = consensusData ? consensusData.sell_rate : window.GLOBAL_CONSENSUS_SELL_RATE;

  if (!buyRate || !sellRate) return;

  const buyTotal = amount * buyRate;
  const sellTotal = amount * sellRate;
  const profit = sellTotal - buyTotal;

  buyEl.textContent = `DOP ${fmtNumber(buyTotal)}`;
  sellEl.textContent = `DOP ${fmtNumber(sellTotal)}`;
  profitEl.textContent = `+DOP ${fmtNumber(profit)}`;
}

document.addEventListener('DOMContentLoaded', () => {
  const calcAmount = document.getElementById('calc-amount');
  if (calcAmount) {
    calcAmount.addEventListener('input', (e) => {
      updateCalculator(parseFloat(e.target.value));
    });
    // Valor inicial
    calcAmount.value = '500';
    updateCalculator(500);
  }
});

// ============================================================================ 
// Filtros de Proveedores
// ============================================================================ 
let allProviderRows = [];

function captureProviderRows() {
  const tbody = document.getElementById('provider-table-body');
  if (!tbody) return;
  
  allProviderRows = Array.from(tbody.querySelectorAll('tr')).map(row => {
    const cells = row.querySelectorAll('td');
    if (cells.length < 6) return null;
    return {
      element: row,
      name: cells[0].textContent.trim().toLowerCase(),
      enabled: cells[1].textContent.trim().includes('Sí'),
      origin: cells[2].textContent.trim().toLowerCase()
    };
  }).filter(r => r !== null);
}

function applyProviderFilters() {
  const searchInput = document.getElementById('provider-search');
  const statusFilter = document.getElementById('provider-status-filter');
  const originFilter = document.getElementById('provider-origin-filter');
  
  const searchVal = searchInput ? searchInput.value.toLowerCase() : '';
  const statusVal = statusFilter ? statusFilter.value : 'all';
  const originVal = originFilter ? originFilter.value : 'all';
  
  let visibleCount = 0;

  allProviderRows.forEach(row => {
    let visible = true;

    if (searchVal && !row.name.includes(searchVal)) visible = false;
    
    if (statusVal === 'active' && !row.enabled) visible = false;
    else if (statusVal === 'inactive' && row.enabled) visible = false;

    if (originVal !== 'all' && !row.origin.includes(originVal.toLowerCase())) visible = false;

    row.element.style.display = visible ? '' : 'none';
    if (visible) visibleCount++;
  });

  const visibleSpan = document.getElementById('visible-count');
  if (visibleSpan) visibleSpan.textContent = visibleCount;
}

document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('provider-search');
  const statusF = document.getElementById('provider-status-filter');
  const originF = document.getElementById('provider-origin-filter');
  const clearBtn = document.getElementById('clear-filters-btn');

  if (search) search.addEventListener('input', applyProviderFilters);
  if (statusF) statusF.addEventListener('change', applyProviderFilters);
  if (originF) originF.addEventListener('change', applyProviderFilters);
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (search) search.value = '';
      if (statusF) statusF.value = 'all';
      if (originF) originF.value = 'all';
      applyProviderFilters();
      showToast('Filtros de proveedores limpiados', 'info');
    });
  }

  // Capturar inicial
  captureProviderRows();
});

// ============================================================================ 
// Comparación de Proveedores
// ============================================================================ 
function updateComparison() {
  const p1 = document.getElementById('provider-1').value;
  const p2 = document.getElementById('provider-2').value;
  const container = document.getElementById('comparison-results-container');
  if (!container) return;

  if (!p1 || !p2) {
    container.innerHTML = `<div class="empty-state-small"><p>Selecciona dos proveedores para iniciar la comparación.</p></div>`;
    return;
  }

  const list = window.GLOBAL_PROVIDER_STATUS_JSON || [];
  const data1 = list.find(p => p.name === p1);
  const data2 = list.find(p => p.name === p2);

  if (!data1 || !data2) {
    container.innerHTML = `<div class="empty-state-small"><p>Error: Datos no disponibles.</p></div>`;
    return;
  }

  const spread1 = (data1.sell_rate && data1.buy_rate) ? data1.sell_rate - data1.buy_rate : null;
  const spread2 = (data2.sell_rate && data2.buy_rate) ? data2.sell_rate - data2.buy_rate : null;

  const winner = (v1, v2, lowerIsBetter = false) => {
    if (v1 === null || v2 === null || v1 === v2) return ['', ''];
    if (lowerIsBetter) return v1 < v2 ? ['winner', ''] : ['', 'winner'];
    return v1 > v2 ? ['winner', ''] : ['', 'winner'];
  };

  const [wBuy1, wBuy2] = winner(data1.buy_rate, data2.buy_rate, false);
  const [wSell1, wSell2] = winner(data1.sell_rate, data2.sell_rate, true);
  const [wSpread1, wSpread2] = winner(spread1, spread2, true);

  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Métrica</th>
          <th>${data1.name}</th>
          <th>${data2.name}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Compra (Vender USD)</td>
          <td class="${wBuy1}">${fmtNumber(data1.buy_rate)}</td>
          <td class="${wBuy2}">${fmtNumber(data2.buy_rate)}</td>
        </tr>
        <tr>
          <td>Venta (Comprar USD)</td>
          <td class="${wSell1}">${fmtNumber(data1.sell_rate)}</td>
          <td class="${wSell2}">${fmtNumber(data2.sell_rate)}</td>
        </tr>
        <tr>
          <td>Spread</td>
          <td class="${wSpread1}">${fmtNumber(spread1, 3)}</td>
          <td class="${wSpread2}">${fmtNumber(spread2, 3)}</td>
        </tr>
      </tbody>
    </table>
  `;
}

document.addEventListener('DOMContentLoaded', () => {
  const p1 = document.getElementById('provider-1');
  const p2 = document.getElementById('provider-2');
  if (p1) p1.addEventListener('change', updateComparison);
  if (p2) p2.addEventListener('change', updateComparison);
});

// ============================================================================ 
// Edición y Eliminación de Trades (Operaciones)
// ============================================================================ 
document.addEventListener('click', async (event) => {
  // Editar Trade (Abrir modal con datos)
  if (event.target.classList.contains('btn-edit-trade')) {
    const tradeId = event.target.dataset.tradeId;
    if (!tradeId) return;

    const tr = event.target.closest('tr');
    if (!tr) return;

    const action = tr.children[1].textContent.trim().toLowerCase();
    const usd = parseFloat(tr.children[2].textContent.replace(/[^\d.-]/g, ''));
    const rate = parseFloat(tr.children[3].textContent.replace(/[^\d.-]/g, ''));
    
    openTradeModal({
      id: tradeId,
      action: action,
      usd_amount: usd,
      rate: rate
    });
  }

  // Eliminar Trade (Llamada API con animación fade-out)
  if (event.target.classList.contains('btn-delete-trade')) {
    const tradeId = event.target.dataset.tradeId;
    if (!tradeId) return;

    if (confirm(`¿Estás seguro de que quieres eliminar el registro #${tradeId}?`)) {
      const tr = event.target.closest('tr');
      if (tr) {
        tr.style.opacity = '0.4'; // visual state
      }

      try {
        const response = await fetch(`/api/trade/${tradeId}`, { method: 'DELETE' });
        if (!response.ok) {
          throw new Error("No se pudo eliminar de la base de datos.");
        }

        showToast(`Registro #${tradeId} eliminado exitosamente.`, 'success');
        
        // Animación suave de eliminación
        if (tr) {
          tr.classList.add('removing-row');
          setTimeout(() => {
            tr.remove();
            refreshDashboardData(); // Recalcula KPIs tras eliminar fila
          }, 300);
        }

      } catch (err) {
        showToast(err.message, 'error');
        if (tr) tr.style.opacity = '1';
      }
    }
  }
});

// ============================================================================ 
// Sidebar de Métricas Clave
// ============================================================================ 
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('metrics-sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle');
  const overlay = document.getElementById('sidebar-overlay');
  const closeBtn = document.getElementById('metrics-sidebar')?.querySelector('.sidebar-close-btn');

  function openSidebar() {
    if (sidebar) sidebar.classList.add('active');
    if (overlay) overlay.style.display = 'block';
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('active');
    if (overlay) overlay.style.display = 'none';
  }

  if (toggleBtn) toggleBtn.addEventListener('click', openSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
  if (overlay) overlay.addEventListener('click', closeSidebar);
});

// ============================================================================ 
// Comandos Manuales Ejecución
// ============================================================================ 
document.addEventListener('DOMContentLoaded', () => {
  const commandButtons = document.querySelectorAll(".command-btn[data-endpoint]");
  commandButtons.forEach(button => {
    button.addEventListener("click", async () => {
      const endpoint = button.dataset.endpoint;
      const method = button.dataset.method || "POST";
      const statusElement = button.closest("li")?.querySelector(".command-status") || document.getElementById('hero-status');

      if (!endpoint) return;

      const oldText = button.textContent;
      button.disabled = true;
      button.textContent = "⌛ Ejecutando...";
      if (statusElement) statusElement.textContent = "Procesando petición en segundo plano...";

      try {
        const response = await fetch(endpoint, { method });
        if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
        
        showToast("Comando completado exitosamente", "success");
        if (statusElement) statusElement.textContent = "Comando completado exitosamente. Sincronizando panel...";
        
        // Sincronización SPA local inmediata
        refreshDashboardData(true);

      } catch (err) {
        console.error(err);
        showToast(`Error al ejecutar: ${err.message}`, "error");
        if (statusElement) statusElement.textContent = `❌ Error: ${err.message}`;
      } finally {
        button.disabled = false;
        button.textContent = oldText;
      }
    });
  });
});

// ============================================================================ 
// Manejo del Cambio de Tema (Modo Oscuro / Claro)
// ============================================================================ 
function initThemeToggle() {
  const toggleBtn = document.getElementById("theme-toggle");
  if (!toggleBtn) return;

  const iconEl = toggleBtn.querySelector("[data-theme-icon]");
  const labelEl = toggleBtn.querySelector("[data-theme-label]");

  function updateToggleButton(theme) {
    if (theme === "dark") {
      if (iconEl) iconEl.textContent = "🌙";
      if (labelEl) labelEl.textContent = "Modo oscuro";
      toggleBtn.setAttribute("aria-pressed", "true");
    } else {
      if (iconEl) iconEl.textContent = "☀️";
      if (labelEl) labelEl.textContent = "Modo claro";
      toggleBtn.setAttribute("aria-pressed", "false");
    }
  }

  // Inicializar el estado del botón según el atributo actual del document Element
  const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
  updateToggleButton(currentTheme);

  toggleBtn.addEventListener("click", async () => {
    const activeTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", activeTheme);
    window.localStorage.setItem("cambio-theme", activeTheme);
    updateToggleButton(activeTheme);

    // Re-renderizar el gráfico si existe para actualizar colores de cuadrícula y etiquetas
    if (trendChart) {
      await renderChart(currentChartPeriod);
    }
    
    showToast(`Tema cambiado a modo ${activeTheme === "dark" ? "oscuro" : "claro"}`, "success");
  });
}

// ============================================================================ 
// Inicialización del Dashboard al Cargar DOM
// ============================================================================ 
document.addEventListener('DOMContentLoaded', () => {
  // 1. Iniciar tiempo transcurrido
  setInterval(() => {
    const timeAgoElement = document.getElementById('time-ago');
    if (timeAgoElement) {
      timeAgoElement.textContent = updateTimeAgo(lastUpdateTimestamp);
    }
  }, 5000);

  // 2. Iniciar SSE
  initSSE();

  // 3. Renderizar Gráfico Inicial (24 horas)
  renderChart(24);

  // 4. Registrar callback para refrescar y renderizar al cambiar tamaño de ventana
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      if (trendChart) trendChart.resize();
    }, 150);
  });

  // 5. Iniciar tema
  initThemeToggle();
});

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

// Test script to check Chart.js loading
(function() {
  console.log('=== INICIO DE DEPURACIÓN ===');
  console.log('Chart.js loaded:', typeof Chart);
  console.log('Canvas exists:', !!document.getElementById('trend-chart'));
  console.log('Document readyState:', document.readyState);

  // Verificar que las funciones existen
  console.log('renderChart function exists:', typeof renderChart);
  console.log('loadChartData function exists:', typeof loadChartData);
  console.log('processChartData function exists:', typeof processChartData);
  console.log('calculateStats function exists:', typeof calculateStats);

  console.log('=== FIN DE DEPURACIÓN ===');
})();

// Función para enviar logs al servidor
async function sendLog(message) {
  try {
    await fetch('/api/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
  } catch (error) {
    console.error('Failed to send log:', error);
  }
}

// Funciones de utilidad
function fmtNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '—';
  return Number(value).toFixed(decimals);
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

function updateTimeAgo(timestamp) {
  if (!timestamp) return '—';
  
  const now = new Date();
  const diff = now - timestamp;
  
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (seconds < 60) return 'ahora mismo';
  if (minutes < 60) return `hace ${minutes}m`;
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${days}d`;
}

document.addEventListener('DOMContentLoaded', function() {
  console.log('🚀 DOMContentLoaded EVENT FIRED - Dashboard initialization starting');
  sendLog('🚀 DOMContentLoaded EVENT FIRED - Dashboard initialization starting');

  // Agregar indicador visual de que el JS se está ejecutando
  const body = document.body;
  body.style.backgroundColor = '#f0f8ff'; // Cambiar fondo para indicar que JS se ejecutó

  // Verificar elementos críticos inmediatamente
  const canvas = document.getElementById('trend-chart');
  console.log('Canvas element check:', { exists: !!canvas, id: canvas?.id });
  sendLog('Canvas element check: ' + JSON.stringify({ exists: !!canvas, id: canvas?.id }));

  if (!canvas) {
    console.error('❌ CRITICAL ERROR: Canvas #trend-chart not found!');
    sendLog('❌ CRITICAL ERROR: Canvas #trend-chart not found!');
    // Agregar mensaje visible en la página
    const errorDiv = document.createElement('div');
    errorDiv.textContent = 'ERROR: Canvas #trend-chart not found!';
    errorDiv.style.color = 'red';
    errorDiv.style.fontSize = '20px';
    errorDiv.style.position = 'fixed';
    errorDiv.style.top = '10px';
    errorDiv.style.right = '10px';
    errorDiv.style.zIndex = '9999';
    document.body.appendChild(errorDiv);
    return;
  }

  // Verificar Chart.js inmediatamente
  console.log('Chart.js check:', { loaded: typeof Chart, version: Chart?.version });
  sendLog('Chart.js check: ' + JSON.stringify({ loaded: typeof Chart, version: Chart?.version }));

  if (typeof Chart === 'undefined') {
    console.error('❌ CRITICAL ERROR: Chart.js not loaded!');
    sendLog('❌ CRITICAL ERROR: Chart.js not loaded!');
    // Agregar mensaje visible en la página
    const errorDiv = document.createElement('div');
    errorDiv.textContent = 'ERROR: Chart.js not loaded!';
    errorDiv.style.color = 'red';
    errorDiv.style.fontSize = '20px';
    errorDiv.style.position = 'fixed';
    errorDiv.style.top = '40px';
    errorDiv.style.right = '10px';
    errorDiv.style.zIndex = '9999';
    document.body.appendChild(errorDiv);
    return;
  }

  console.log('✅ All prerequisites met, proceeding with renderChart(24)');
  sendLog('✅ All prerequisites met, proceeding with renderChart(24)');
  console.log('Calling renderChart with hours=24');
  sendLog('Calling renderChart with hours=24');

  // Cambiar color del canvas para indicar que renderChart se va a llamar
  canvas.style.border = '2px solid blue';

  renderChart(24).then(() => {
    console.log('✅ renderChart completed successfully');
    sendLog('✅ renderChart completed successfully');
    // Cambiar color del canvas para indicar éxito
    canvas.style.border = '2px solid green';
  }).catch(error => {
    console.error('❌ renderChart failed:', error);
    sendLog('❌ renderChart failed: ' + error.message);
    // Cambiar color del canvas para indicar error
    canvas.style.border = '2px solid red';
  });

  // Variables para modo LIVE
  let isLiveMode = false;
  let liveUpdateInterval = null;

  // Variables para auto-refresh
  let autoRefreshInterval = null;
  let timeAgoInterval = null;

  // Variable para el gráfico de Chart.js
  let trendChart = null;

  // Inicializar timestamp de última actualización
  let lastUpdateTimestamp = GLOBAL_CONSENSUS_TIMESTAMP && GLOBAL_CONSENSUS_TIMESTAMP !== '' ? new Date(GLOBAL_CONSENSUS_TIMESTAMP) : new Date();

  // Actualizar indicador cada segundo
  function startTimeAgoUpdater() {
    const timeAgoElement = document.getElementById('time-ago');
    if (!timeAgoElement) return;
    
    timeAgoInterval = setInterval(() => {
      timeAgoElement.textContent = updateTimeAgo(lastUpdateTimestamp);
    }, 1000);
    
    // Actualización inicial
    timeAgoElement.textContent = updateTimeAgo(lastUpdateTimestamp);
  }

  // Función para actualizar el dashboard con nuevos datos
  async function refreshDashboardData() {
    try {
      const response = await fetch('/api/consensus');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      
      // Actualizar timestamp siempre que se refresca
      lastUpdateTimestamp = data.timestamp ? new Date(data.timestamp) : new Date();
      
      // Actualizar consenso en chips
      const midChip = document.querySelector('.chip-positive');
      if (midChip && data.mid_rate) {
        midChip.textContent = `📊 Mid ${data.mid_rate.toFixed(2)} DOP`;
      }
      
      // Actualizar resumen
      const summary = document.querySelector('.hero-summary');
      if (summary) {
        summary.textContent = `Seguimiento en tiempo real al consenso del mercado: mid ${data.mid_rate.toFixed(2)} DOP, divergencia ${data.divergence_range.toFixed(3)} y activo.`;
      }
      
      // Actualizar calculadora si hay valor
      const calcAmount = document.getElementById('calc-amount');
      if (calcAmount && calcAmount.value) {
        updateCalculator(parseFloat(calcAmount.value), data);
      }
      
      return data;
    } catch (error) {
      console.error('Error refreshing data:', error);
      // Incluso en error, actualizar timestamp para mostrar que se intentó
      lastUpdateTimestamp = new Date();
      return null;
    }
  }

  // Auto-refresh cada 30 segundos
  function startAutoRefresh() {
    autoRefreshInterval = setInterval(async () => {
      const data = await refreshDashboardData();
      if (data) {
        // Solo mostrar toast si la página está visible
        if (document.visibilityState === 'visible') {
          showToast('Dashboard actualizado automáticamente', 'info');
        }
      }
    }, 30000); // 30 segundos
  }

  // Botón de refresh manual
  const manualRefreshBtn = document.getElementById('manual-refresh-btn');
  if (manualRefreshBtn) {
    manualRefreshBtn.addEventListener('click', async () => {
      manualRefreshBtn.disabled = true;
      manualRefreshBtn.textContent = '🔄 Actualizando...';
      
      const data = await refreshDashboardData();
      if (data) {
        showToast('Dashboard actualizado exitosamente. Recargando...', 'success');
        // Recargar la página para actualizar todas las secciones
        setTimeout(() => location.reload(), 500);
      } else {
        showToast('Error al actualizar el dashboard', 'error');
      }
      
      manualRefreshBtn.disabled = false;
      manualRefreshBtn.textContent = '🔄 Refrescar ahora';
    });
  }

  // ============================================================================ 
  // Calculadora Rápida
  // ============================================================================ 
  
  const calcAmountInput = document.getElementById('calc-amount');
  const calcBuyElement = document.getElementById('calc-buy');
  const calcSellElement = document.getElementById('calc-sell');
  const calcProfitElement = document.getElementById('calc-profit');
  
  function updateCalculator(amount, consensusData = null) {
    if (!amount || amount <= 0) {
      calcBuyElement.textContent = '—';
      calcSellElement.textContent = '—';
      calcProfitElement.textContent = '—';
      return;
    }
    
    // Usar datos del consenso actual o del parámetro
    const buyRate = consensusData ? consensusData.buy_rate : GLOBAL_CONSENSUS_BUY_RATE;
    const sellRate = consensusData ? consensusData.sell_rate : GLOBAL_CONSENSUS_SELL_RATE;
    
    if (!buyRate || !sellRate) {
      calcBuyElement.textContent = '—';
      calcSellElement.textContent = '—';
      calcProfitElement.textContent = '—';
      return;
    }
    
    const buyTotal = amount * buyRate;
    const sellTotal = amount * sellRate;
    const profit = sellTotal - buyTotal;
    
    calcBuyElement.textContent = `DOP ${buyTotal.toFixed(2)}`;
    calcSellElement.textContent = `DOP ${sellTotal.toFixed(2)}`;
    calcProfitElement.textContent = `${profit >= 0 ? '+' : ''}DOP ${profit.toFixed(2)}`;
    calcProfitElement.style.color = profit >= 0 ? '#10b981' : '#ef4444';
  }
  
  if (calcAmountInput) {
    calcAmountInput.addEventListener('input', (e) => {
      const amount = parseFloat(e.target.value);
      updateCalculator(amount);
    });
    
    // Calcular con ejemplo inicial si hay consenso
    if (GLOBAL_CONSENSUS_BUY_RATE) {
      setTimeout(() => {
        calcAmountInput.value = '500';
        updateCalculator(500);
      }, 1000);
    }
  }

  // ============================================================================ 
  // Gráfico de Tendencia con Chart.js
  // ============================================================================ 
  
  async function loadChartData(hours = 24) {
    console.log('loadChartData llamado con hours:', hours);
    try {
      const minutes = hours * 60;
      console.log('Haciendo fetch a:', `/api/snapshots?minutes=${minutes}`);
      const response = await fetch(`/api/snapshots?minutes=${minutes}`);
      console.log('Respuesta del fetch:', response.status, response.statusText);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const snapshots = await response.json();
      console.log('Datos JSON obtenidos:', snapshots.length, 'registros');
      return snapshots;
    } catch (error) {
      console.error('Error loading chart data:', error);
      return [];
    }
  }

  function processChartData(snapshots) {
    if (!snapshots || snapshots.length === 0) {
      return { labels: [], buyRates: [], sellRates: [] };
    }

    // Agrupar por timestamp para promediar (evitar múltiples proveedores al mismo tiempo)
    const grouped = {};
    snapshots.forEach(snap => {
      const timestamp = new Date(snap.timestamp).getTime();
      if (!grouped[timestamp]) {
        grouped[timestamp] = { buy: [], sell: [], timestamp: snap.timestamp };
      }
      grouped[timestamp].buy.push(snap.buy_rate);
      grouped[timestamp].sell.push(snap.sell_rate);
    });

    // Promediar y ordenar
    const processed = Object.values(grouped)
      .map(group => ({
        timestamp: group.timestamp,
        buyRate: group.buy.reduce((a, b) => a + b, 0) / group.buy.length,
        sellRate: group.sell.reduce((a, b) => a + b, 0) / group.sell.length
      }))
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    // Reducir puntos si hay muchos (mostrar cada N puntos)
    const maxPoints = 50;
    const step = Math.ceil(processed.length / maxPoints);
    const reduced = processed.filter((_, index) => index % step === 0);

    return {
      labels: reduced.map(d => {
        const date = new Date(d.timestamp);
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
      }),
      buyRates: reduced.map(d => d.buyRate),
      sellRates: reduced.map(d => d.sellRate),
      rawData: processed
    };
  }

  function calculateStats(data) {
    if (!data || data.length === 0) return null;

    const buyRates = data.map(d => d.buyRate);
    const sellRates = data.map(d => d.sellRate);

    const avgBuy = buyRates.reduce((a, b) => a + b, 0) / buyRates.length;
    const avgSell = sellRates.reduce((a, b) => a + b, 0) / sellRates.length;

    // Volatilidad (desviación estándar)
    const variance = buyRates.reduce((sum, rate) => sum + Math.pow(rate - avgBuy, 2), 0) / buyRates.length;
    const volatility = Math.sqrt(variance);

    // Tendencia (comparar primeros 25% vs últimos 25%)
    const quarter = Math.floor(data.length / 4);
    const firstQuarter = buyRates.slice(0, quarter).reduce((a, b) => a + b, 0) / quarter;
    const lastQuarter = buyRates.slice(-quarter).reduce((a, b) => a + b, 0) / quarter;
    const trend = lastQuarter - firstQuarter;

    return { avgBuy, avgSell, volatility, trend };
  }

  async function renderChart(hours = 24) {
    console.log('🚀 Iniciando renderChart con hours:', hours);
    sendLog('🚀 Iniciando renderChart con hours: ' + hours);

    // Verificar que el canvas existe
    const canvasElement = document.getElementById('trend-chart');
    if (!canvasElement) {
      console.error('❌ ERROR: Canvas #trend-chart no encontrado');
      return;
    }
    console.log('✅ Canvas encontrado');

    // Verificar que Chart.js está cargado
    if (typeof Chart === 'undefined') {
      console.error('❌ ERROR: Chart.js no está cargado');
      return;
    }
    console.log('✅ Chart.js disponible');

    try {
      // Destruir chart anterior si existe
      if (trendChart) {
        console.log('Destruyendo chart anterior');
        trendChart.destroy();
      }

      const ctx = canvasElement.getContext('2d');
      console.log('Canvas context:', ctx);

      // Crear un gráfico muy simple para probar
      console.log('🔄 Creando gráfico de prueba...');
      trendChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: ['10:00', '11:00', '12:00', '13:00', '14:00'],
          datasets: [{
            label: 'Prueba',
            data: [63.0, 63.2, 63.1, 63.3, 63.4],
            borderColor: '#4cc3ff',
            backgroundColor: 'rgba(76, 195, 255, 0.15)',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false
        }
      });

      console.log('✅ Gráfico de prueba creado exitosamente');

      // Ahora intentar cargar datos reales
      console.log('🔄 Cargando datos reales...');
      const snapshots = await loadChartData(hours);
      console.log('✅ Datos obtenidos:', snapshots.length, 'registros');

      if (snapshots.length > 0) {
        const chartData = processChartData(snapshots);
        const stats = calculateStats(chartData.rawData);

        console.log('🔄 Actualizando gráfico con datos reales...');
        trendChart.data.labels = chartData.labels;
        trendChart.data.datasets = [
          {
            label: 'Compra',
            data: chartData.buyRates,
            borderColor: '#4cc3ff',
            backgroundColor: 'rgba(76, 195, 255, 0.15)',
            borderWidth: 2,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: '#4cc3ff',
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2
          },
          {
            label: 'Venta',
            data: chartData.sellRates,
            borderColor: '#5de4d6',
            backgroundColor: 'rgba(93, 228, 214, 0.15)',
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: '#5de4d6',
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2
          }
        ];

        // Actualizar opciones con configuración completa
        trendChart.options = {
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
                color: 'rgba(241, 247, 255, 0.9)',
                font: {
                  size: 12,
                  weight: '600'
                },
                padding: 15,
                usePointStyle: true,
                pointStyle: 'circle'
              }
            },
            tooltip: {
              enabled: true,
              backgroundColor: 'rgba(13, 20, 31, 0.95)',
              titleColor: '#f1f7ff',
              bodyColor: '#f1f7ff',
              borderColor: 'rgba(151, 217, 255, 0.3)',
              borderWidth: 1,
              padding: 12,
              displayColors: true,
              callbacks: {
                label: function(context) {
                  return ` ${context.dataset.label}: ${context.parsed.y.toFixed(2)} DOP`;
                }
              }
            }
          },
          scales: {
            x: {
              grid: {
                color: 'rgba(151, 217, 255, 0.08)',
                drawBorder: false
              },
              ticks: {
                color: 'rgba(241, 247, 255, 0.6)',
                font: {
                  size: 10
                },
                maxRotation: 45,
                minRotation: 0
              }
            },
            y: {
              beginAtZero: false,
              grid: {
                color: 'rgba(151, 217, 255, 0.08)',
                drawBorder: false
              },
              ticks: {
                color: 'rgba(241, 247, 255, 0.6)',
                font: {
                  size: 11
                },
                callback: function(value) {
                  return value.toFixed(2) + ' DOP';
                }
              }
            }
          }
        };

        // Actualizar stats si existen
        if (stats) {
          const avgBuyEl = document.getElementById('chart-avg-buy');
          const avgSellEl = document.getElementById('chart-avg-sell');
          const volatilityEl = document.getElementById('chart-volatility');
          const trendEl = document.getElementById('chart-trend');

          if (avgBuyEl) avgBuyEl.textContent = stats.avgBuy.toFixed(2) + ' DOP';
          if (avgSellEl) avgSellEl.textContent = stats.avgSell.toFixed(2) + ' DOP';

          if (volatilityEl) {
            const volatilityLevel = stats.volatility < 0.2 ? 'Baja' : stats.volatility < 0.5 ? 'Media' : 'Alta';
            volatilityEl.textContent = volatilityLevel + ` (${stats.volatility.toFixed(3)})`;
          }

          if (trendEl) {
            const trendText = stats.trend > 0.05 ? '📈 Alcista' : stats.trend < -0.05 ? '📉 Bajista' : '➡️ Estable';
            const trendColor = stats.trend > 0.05 ? '#10b981' : stats.trend < -0.05 ? '#ef4444' : '#ffc961';
            trendEl.textContent = trendText;
            trendEl.style.color = trendColor;
          }
        }

        trendChart.update();
        console.log('✅ Gráfico actualizado con datos reales');
      }

    } catch (error) {
      console.error('❌ Error en renderChart:', error);
    }
  }

  // Event listeners para botones de período
  const periodButtons = document.querySelectorAll('.chart-period-btn');
  periodButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      // Si ya está en modo LIVE y se hace clic en otro botón, detener LIVE
      if (isLiveMode && !btn.classList.contains('live-btn')) {
        clearInterval(liveUpdateInterval);
        liveUpdateInterval = null;
        isLiveMode = false;
        showToast('Modo LIVE desactivado', 'info');
      }

      // Remover active de todos
      periodButtons.forEach(b => {
        b.classList.remove('active');
        b.style.borderColor = 'rgba(151, 217, 255, 0.2)';
        b.style.background = 'rgba(76, 195, 255, 0.1)';
        b.style.fontWeight = 'normal';
      });
      
      // Agregar active al clickeado
      btn.classList.add('active');
      btn.style.borderColor = 'rgba(151, 217, 255, 0.4)';
      btn.style.background = 'rgba(76, 195, 255, 0.25)';
      btn.style.fontWeight = '600';
      
      const hours = parseFloat(btn.dataset.hours);
      currentChartPeriod = hours;

      // Manejo especial para botón LIVE
      if (btn.classList.contains('live-btn')) {
        // Activar modo LIVE
        isLiveMode = true;
        await renderChart(hours);
        
        // Configurar actualizaciones automáticas cada 30 segundos
        liveUpdateInterval = setInterval(async () => {
          try {
            await renderChart(hours);
          } catch (error) {
            console.error('Error en actualización LIVE:', error);
            // Si hay error, detener las actualizaciones
            clearInterval(liveUpdateInterval);
            liveUpdateInterval = null;
            isLiveMode = false;
            showToast('Error en modo LIVE, actualizaciones detenidas', 'error');
          }
        }, 30000); // 30 segundos
        
        showToast('Modo LIVE activado: actualizaciones cada 30s', 'success');
      } else {
        // Para otros botones, renderizar una vez
        await renderChart(hours);
        showToast(`Gráfico actualizado: últimas ${hours}h`, 'info');
      }
    });
  });

  // ============================================================================ 
  // Filtros de Tabla de Proveedores
  // ============================================================================ 
  
  const providerSearchInput = document.getElementById('provider-search');
  const providerStatusFilter = document.getElementById('provider-status-filter');
  const providerOriginFilter = document.getElementById('provider-origin-filter');
  const clearFiltersBtn = document.getElementById('clear-filters-btn');
  const visibleCountSpan = document.getElementById('visible-count');
  
  // Capturar todas las filas al cargar
  function captureProviderRows() {
    if (!providerTableBody) return;
    
    allProviderRows = Array.from(providerTableBody.querySelectorAll('tr')).map(row => {
      const cells = row.querySelectorAll('td');
      if (cells.length < 6) return null;
      
      return {
        element: row,
        name: cells[0].textContent.trim().toLowerCase(),
        enabled: cells[1].textContent.trim().toLowerCase() === 'sí',
        origin: cells[2].textContent.trim().toLowerCase(),
        buyRate: cells[3].textContent.trim(),
        sellRate: cells[4].textContent.trim(),
        updated: cells[5].textContent.trim()
      };
    }).filter(row => row !== null);
  }
  
  // Aplicar filtros
  function applyProviderFilters() {
    if (allProviderRows.length === 0) {
      captureProviderRows();
    }
    
    const searchTerm = providerSearchInput ? providerSearchInput.value.toLowerCase() : '';
    const statusFilter = providerStatusFilter ? providerStatusFilter.value : 'all';
    const originFilter = providerOriginFilter ? providerOriginFilter.value : 'all';
    
    let visibleCount = 0;
    
    allProviderRows.forEach(row => {
      let visible = true;
      
      // Filtro de búsqueda
      if (searchTerm && !row.name.includes(searchTerm)) {
        visible = false;
      }
      
      // Filtro de estado
      if (statusFilter === 'active' && !row.enabled) {
        visible = false;
      } else if (statusFilter === 'inactive' && row.enabled) {
        visible = false;
      }
      
      // Filtro de origen
      if (originFilter !== 'all' && !row.origin.includes(originFilter.toLowerCase())) {
        visible = false;
      }
      
      // Mostrar/ocultar fila
      row.element.style.display = visible ? '' : 'none';
      
      if (visible) visibleCount++;
    });
    
    // Actualizar contador
    if (visibleCountSpan) {
      visibleCountSpan.textContent = visibleCount;
    }
    
    // Mostrar mensaje si no hay resultados
    if (visibleCount === 0 && providerTableBody) {
      const existingMsg = providerTableBody.querySelector('.no-results-message');
      if (!existingMsg) {
        const noResultsRow = document.createElement('tr');
        noResultsRow.className = 'no-results-message';
        noResultsRow.innerHTML = `
          <td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔍</div>
            <div style="font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem;">No se encontraron proveedores</div>
            <div style="font-size: 0.85rem;">Intenta ajustar los filtros de búsqueda</div>
          </td>
        `;
        providerTableBody.appendChild(noResultsRow);
      }
    } else {
      const existingMsg = providerTableBody.querySelector('.no-results-message');
      if (existingMsg) existingMsg.remove();
    }
    
    return visibleCount;
  }
  
  // Event listeners para filtros
  if (providerSearchInput) {
    providerSearchInput.addEventListener('input', () => {
      applyProviderFilters();
    });
  }
  
  if (providerStatusFilter) {
    providerStatusFilter.addEventListener('change', () => {
      const count = applyProviderFilters();
      showToast(`Filtro aplicado: ${count} proveedores visibles`, 'info');
    });
  }
  
  if (providerOriginFilter) {
    providerOriginFilter.addEventListener('change', () => {
      const count = applyProviderFilters();
      showToast(`Filtro aplicado: ${count} proveedores visibles`, 'info');
    });
  }
  
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', () => {
      if (providerSearchInput) providerSearchInput.value = '';
      if (providerStatusFilter) providerStatusFilter.value = 'all';
      if (providerOriginFilter) providerOriginFilter.value = 'all';
      
      const count = applyProviderFilters();
      showToast(`Filtros limpiados: ${count} proveedores visibles`, 'success');
    });
  }

  // ============================================================================ 
  // Función para actualizar tabla de proveedores (usada por comandos)
  // ============================================================================ 
  function updateProvidersTable(providers) {
    if (!Array.isArray(providers) || !providerTableBody) return;

    // Limpiar tabla actual
    providerTableBody.innerHTML = '';

    // Agregar filas actualizadas
    providers.forEach(provider => {
      const row = document.createElement('tr');
      const enabledText = provider.enabled ? 'Sí' : 'No';
      const enabledClass = provider.enabled ? 'status-enabled' : 'status-disabled';
      const buyRate = provider.buy_rate ? provider.buy_rate.toFixed(2) : '—';
      const sellRate = provider.sell_rate ? provider.sell_rate.toFixed(2) : '—';
      const lastUpdate = provider.last_timestamp ? new Date(provider.last_timestamp).toLocaleString() : 'Nunca';

      row.innerHTML = `
        <td>${escapeHtml(provider.name)}</td>
        <td><span class="status-badge ${enabledClass}">${enabledText}</span></td>
        <td>${escapeHtml(provider.origin || '—')}</td>
        <td>${buyRate}</td>
        <td>${sellRate}</td>
        <td>${lastUpdate}</td>
      `;

      providerTableBody.appendChild(row);
    });

    // Recapturar filas para filtros después de actualizar
    allProviderRows = [];
    captureProviderRows();
    applyProviderFilters();
  }

  // ============================================================================ 
  // Lógica de Comandos y UI
  // ============================================================================ 

  const formatters = {
    fetch: (data, extras) => {
      const consensus = extras?.consensus;
      const providersList = extras?.providers;
      if (consensus) {
        const providers = providersList?.length || consensus.providers_considered?.length || 0;
        const divergence = fmtNumber(consensus.divergence_range, 3);
        return [
          "Captura solicitada y en curso.",
          `Último consenso: ${fmtNumber(consensus.buy_rate)} / ${fmtNumber(consensus.sell_rate)}`,
          `Proveedores activos: ${providers} · Divergencia: ${divergence}`,
        ].join("\n");
      }
      return data?.detail || "Captura solicitada.";
    },
    analyze: (data) => {
      if (!data) return "Recomendación generada.";
      const suggestedBuy = data.suggested_buy_rate !== null ? fmtNumber(data.suggested_buy_rate) : "—";
      const suggestedSell = data.suggested_sell_rate !== null ? fmtNumber(data.suggested_sell_rate) : "—";
      const advantage = data.spread_advantage !== null ? fmtNumber(data.spread_advantage, 3) : "—";
      return [
        `${data.action.toUpperCase()} · Ganancia esperada ${fmtNumber(data.expected_profit)} DOP · Confianza ${fmtNumber(data.score * 100, 1)}%`,
        `Compra sugerida: ${suggestedBuy} | Venta sugerida: ${suggestedSell}`,
        `Ventaja vs mercado: ${advantage}`,
        `Motivo: ${shortText(data.reason, 140)}`,
      ].join("\n");
    },
    forecast: (data) => {
      if (!data) return "Pronóstico actualizado.";
      return [
        `Esperado: ${fmtNumber(data.expected_profit_end_day)} DOP`,
        `Mejor caso: ${fmtNumber(data.best_case)} | Peor caso: ${fmtNumber(data.worst_case)}`,
        `Confianza ±${fmtNumber(data.confidence_interval)} · ${shortText(data.details, 120)}`,
      ].join("\n");
    },
    compare: (data) => {
      if (!data) return "Comparación generada.";
      const flagged = Array.isArray(data.validations)
        ? data.validations.filter((item) => item.flagged).length
        : 0;
      return [
        `Consenso ${fmtNumber(data.buy_rate)} / ${fmtNumber(data.sell_rate)} · ${data.providers_considered?.length || 0} proveedores`,
        `Divergencia: ${fmtNumber(data.divergence_range, 3)} · Outliers: ${flagged}`,
      ].join("\n");
    },
    providers: (data) => {
      if (!Array.isArray(data)) return "Consulta completada.";
      const enabled = data.filter((provider) => provider.enabled).length;
      const total = data.length;
      const recent = data
        .filter((provider) => provider.last_timestamp)
        .slice(0, 3)
        .map((provider) => provider.name)
        .join(", ") || "sin actualizaciones";
      return [
        `Proveedores habilitados: ${enabled}/${total}`,
        `Actualizados recientemente: ${recent}`,
      ].join("\n");
    },
    history: (data) => {
      if (!Array.isArray(data) || data.length === 0) {
        return "Sin operaciones registradas.";
      }
      const [latest] = data;
      const when = latest.timestamp ? new Date(latest.timestamp).toLocaleString() : "Fecha N/D";
      return [
        `${data.length} operaciones registradas.`,
        `Última: ${latest.action?.toUpperCase() || "N/A"} · USD ${fmtNumber(latest.usd_amount)} a ${fmtNumber(latest.rate)}`,
        `Ganancia estimada: ${fmtNumber(latest.profit_dop)} DOP · ${when}`,
      ].join("\n");
    },
    drift: (data) => {
      if (!Array.isArray(data) || data.length === 0) {
        return "Sin eventos de drift registrados.";
      }
      const [latest] = data;
      const arrow = latest.direction === "UP" ? "↑" : "↓";
      return [
        `${data.length} eventos en historial.`,
        `Último: ${arrow} ${latest.direction} · ${fmtNumber(latest.value, 3)} DOP`,
        `EWMA ${fmtNumber(latest.ewma, 3)} · Umbral ${fmtNumber(latest.threshold, 3)}`,
      ].join("\n");
    },
  };

  const extraFetchers = {
    fetch: async () => {
      const results = {};
      try {
        const response = await fetch("/api/consensus");
        if (response.ok) {
          results.consensus = await response.json();
        }
      } catch (error) {
        console.warn("No se pudo obtener consenso tras la captura", error);
      }
      try {
        const providersResponse = await fetch("/api/providers");
        if (providersResponse.ok) {
          results.providers = await providersResponse.json();
        }
      } catch (error) {
        console.warn("No se pudo refrescar proveedores tras la captura", error);
      }
      return results;
    },
  };

  const commandButtons = document.querySelectorAll(".command-btn[data-endpoint], .command-btn[data-command]");
  commandButtons.forEach((button) => {
    if (button.disabled) {
      return;
    }

    button.addEventListener("click", async () => {
      const commandKey = button.dataset.command || "default";

      // Handle trade form toggle specially
      if (commandKey === "trade-form") {
        const form = document.getElementById("trade-form");
        if (form) {
          form.style.display = form.style.display === "none" ? "block" : "none";
        }
        return;
      }

      const endpoint = button.dataset.endpoint;
      const method = button.dataset.method || "POST";
      const statusTarget = button.dataset.statusTarget;
      const statusElement = statusTarget
        ? document.querySelector(statusTarget)
        : button.closest("li")?.querySelector(".command-status");

      if (!endpoint) {
        return;
      }

      const setStatus = (message) => {
        if (statusElement) {
          statusElement.textContent = message;
        }
      };

      setStatus("Ejecutando…");
      button.disabled = true;
      button.classList.add("is-loading");

      try {
        const response = await fetch(endpoint, { method });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || `Error ${response.status}`);
        }

        let payload = null;
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          try {
            payload = await response.json();
          } catch (jsonError) {
            console.warn("No se pudo parsear JSON de respuesta", jsonError);
          }
        }

        const extras = extraFetchers[commandKey] ? await extraFetchers[commandKey]() : null;
        const formatter = formatters[commandKey];
        const message = formatter ? formatter(payload, extras) : payload?.detail || "Comando completado.";
        setStatus(message);

        if (commandKey === "providers" && Array.isArray(payload)) {
          updateProvidersTable(payload);
        } else if (commandKey === "fetch" && extras && Array.isArray(extras.providers)) {
          updateProvidersTable(extras.providers);
        }
      } catch (error) {
        console.error(error);
        setStatus(error.message || "Error inesperado.");
      } finally {
        button.disabled = false;
        button.classList.remove("is-loading");
      }
    });
  });

  // Trade form submit handler
  const tradeSubmitBtn = document.getElementById("trade-submit-btn");
  if (tradeSubmitBtn) {
    tradeSubmitBtn.addEventListener("click", async () => {
      const actionRadio = document.querySelector('input[name="trade-action-radio"]:checked');
      const action = actionRadio ? actionRadio.value : "sell";
      const amount = parseFloat(document.getElementById("trade-amount").value);
      const rateInput = document.getElementById("trade-rate").value;
      const feesInput = document.getElementById("trade-fees").value;
      const resultElement = document.getElementById("trade-result");

      // Limpiar clase de error
      resultElement.classList.remove("error");

      // Validación
      if (!amount || amount <= 0) {
        resultElement.textContent = "❌ Error: El monto en USD debe ser mayor a 0";
        resultElement.classList.add("error");
        return;
      }

      const payload = {
        action: action,
        usd_amount: amount,
      };

      if (rateInput && parseFloat(rateInput) > 0) {
        payload.rate = parseFloat(rateInput);
      }

      if (feesInput && parseFloat(feesInput) >= 0) {
        payload.fees = parseFloat(feesInput);
      }

      resultElement.textContent = "⏳ Registrando operación...";
      resultElement.classList.remove("error");
      tradeSubmitBtn.disabled = true;
      tradeSubmitBtn.textContent = "⏳ Procesando...";

      try {
        const response = await fetch("/api/trade", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Error ${response.status}`);
        }

        const trade = await response.json();
        const actionEmoji = trade.action === "buy" ? "💵" : "💸";
        const profitSign = trade.profit_dop >= 0 ? "+" : "";
        const profitColor = trade.profit_dop >= 0 ? "#10b981" : "#ef4444";

        resultElement.innerHTML = `
          <div style="text-align: center; padding: 0.5rem 0;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">${actionEmoji}</div>
            <div style="font-size: 1.125rem; font-weight: 600; color: #374151; margin-bottom: 0.75rem;">
              ✅ Operación registrada exitosamente
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem; text-align: left;">
              <div style="background: #f9fafb; padding: 0.75rem; border-radius: 6px;">
                <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 0.25rem;">Tipo</div>
                <div style="font-weight: 600; color: #374151;">${trade.action.toUpperCase()}</div>
              </div>
              <div style="background: #f9fafb; padding: 0.75rem; border-radius: 6px;">
                <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 0.25rem;">Monto</div>
                <div style="font-weight: 600; color: #374151;">USD ${fmtNumber(trade.usd_amount)}</div>
              </div>
              <div style="background: #f9fafb; padding: 0.75rem; border-radius: 6px;">
                <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 0.25rem;">Tasa</div>
                <div style="font-weight: 600; color: #374151;">${fmtNumber(trade.rate)} DOP/USD</div>
              </div>
              <div style="background: #f9fafb; padding: 0.75rem; border-radius: 6px;">
                <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 0.25rem;">Ganancia estimada</div>
                <div style="font-weight: 600; color: #374151;">${profitSign}${fmtNumber(trade.profit_dop)} DOP</div>
              </div>
            </div>
            <div style="margin-top: 1rem; font-size: 0.75rem; color: #6b7280;">
              Comisiones: ${fmtNumber(trade.fees)} DOP
            </div>
          </div>
        `;

        // Limpiar formulario después de 3 segundos
        setTimeout(() => {
          document.getElementById("trade-amount").value = "";
          document.getElementById("trade-rate").value = "";
          document.getElementById("trade-fees").value = "";
        }, 3000);
      } catch (error) {
        console.error(error);
        resultElement.textContent = `❌ Error: ${error.message}`;
        resultElement.classList.add("error");
      } finally {
        tradeSubmitBtn.disabled = false;
        tradeSubmitBtn.textContent = "✅ Registrar operación";
      }
    });
  }

  // ============================================================================ 
  // Sidebar de Métricas
  // ============================================================================ 
  console.log('DOM cargado. Configurando la barra lateral...');

  const sidebar = document.getElementById('metrics-sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle');

  if (!sidebar) {
    console.error('Error: No se encontró el elemento de la barra lateral #metrics-sidebar.');
    return;
  }
  if (!toggleBtn) {
    console.error('Error: No se encontró el botón de activación #sidebar-toggle.');
    return;
  }

  console.log('Barra lateral y botón encontrados correctamente.');

  const applySidebarState = (isCollapsed) => {
    console.log(`Aplicando estado: colapsado = ${isCollapsed}`);
    sidebar.classList.toggle('collapsed', isCollapsed);
  };

  // Restaurar estado desde localStorage
  const isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
  console.log(`Restaurando desde localStorage: colapsado = ${isSidebarCollapsed}`);
  applySidebarState(isSidebarCollapsed);

  // Event listener para el botón
  toggleBtn.addEventListener('click', () => {
    const currentlyCollapsed = sidebar.classList.contains('collapsed');
    console.log(`¡Botón clickeado! Estado actual: colapsado = ${currentlyCollapsed}. Cambiando a: ${!currentlyCollapsed}`);
    applySidebarState(!currentlyCollapsed);
    localStorage.setItem('sidebarCollapsed', !currentlyCollapsed);
  });

  // ============================================================================ 
  // Comparación de Proveedores
  // ============================================================================ 
  const providerStatusData = GLOBAL_PROVIDER_STATUS_JSON;

  const provider1Select = document.getElementById('provider-1');
  const provider2Select = document.getElementById('provider-2');
  const comparisonContainer = document.getElementById('comparison-results-container');

  function updateComparison() {
    const name1 = provider1Select.value;
    const name2 = provider2Select.value;

    if (!name1 || !name2) {
      comparisonContainer.innerHTML = `
        <div class="empty-state-small">
          <p>Selecciona dos proveedores para iniciar la comparación.</p>
        </div>`;
      return;
    }

    const data1 = providerStatusData.find(p => p.name === name1);
    const data2 = providerStatusData.find(p => p.name === name2);

    if (!data1 || !data2) {
      comparisonContainer.innerHTML = `<div class="empty-state-small"><p>Error: No se encontraron datos para los proveedores seleccionados.</p></div>`;
      return;
    }

    const spread1 = (data1.sell_rate && data1.buy_rate) ? data1.sell_rate - data1.buy_rate : null;
    const spread2 = (data2.sell_rate && data2.buy_rate) ? data2.sell_rate - data2.buy_rate : null;

    const getWinnerClass = (val1, val2, lowerIsBetter = false) => {
      if (val1 === null || val2 === null || val1 === val2) return ['', ''];
      if (lowerIsBetter) {
        return val1 < val2 ? ['winner', ''] : ['', 'winner'];
      }
      return val1 > val2 ? ['winner', ''] : ['', 'winner'];
    };

    const [buyWinner1, buyWinner2] = getWinnerClass(data1.buy_rate, data2.buy_rate, false); // Higher is better
    const [sellWinner1, sellWinner2] = getWinnerClass(data1.sell_rate, data2.sell_rate, true); // Lower is better
    const [spreadWinner1, spreadWinner2] = getWinnerClass(spread1, spread2, true); // Lower is better

    const time1 = data1.last_timestamp ? new Date(data1.last_timestamp) : null;
    const time2 = data2.last_timestamp ? new Date(data2.last_timestamp) : null;
    const [timeWinner1, timeWinner2] = getWinnerClass(time1, time2, false); // Newer (higher timestamp) is better

    const tableHTML = `
      <table class="comparison-table">
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
            <td class="${buyWinner1}">${data1.buy_rate ? data1.buy_rate.toFixed(2) : '—'}</td>
            <td class="${buyWinner2}">${data2.buy_rate ? data2.buy_rate.toFixed(2) : '—'}</td>
          </tr>
          <tr>
            <td>Venta (Comprar USD)</td>
            <td class="${sellWinner1}">${data1.sell_rate ? data1.sell_rate.toFixed(2) : '—'}</td>
            <td class="${sellWinner2}">${data2.sell_rate ? data2.sell_rate.toFixed(2) : '—'}</td>
          </tr>
          <tr>
            <td>Spread</td>
            <td class="${spreadWinner1}">${spread1 ? spread1.toFixed(3) : '—'}</td>
            <td class="${spreadWinner2}">${spread2 ? spread2.toFixed(3) : '—'}</td>
          </tr>
          <tr>
            <td>Actualización</td>
            <td class="${timeWinner1}">${time1 ? time1.toLocaleTimeString() : '—'}</td>
            <td class="${timeWinner2}">${time2 ? time2.toLocaleTimeString() : '—'}</td>
          </tr>
        </tbody>
      </table>
    `;
    comparisonContainer.innerHTML = tableHTML;
  }

  if (provider1Select && provider2Select) {
    provider1Select.addEventListener('change', updateComparison);
    provider2Select.addEventListener('change', updateComparison);
  }

  // ============================================================================ 
  // Edición y Eliminación de Trades
  // ============================================================================ 
  const tradeHistoryTableBody = document.querySelector('#trade-history-table-body'); // Asumiendo que la tabla tiene un ID

  document.addEventListener('click', async (event) => {
    // Manejar eliminación de trade
    if (event.target.classList.contains('btn-delete-trade')) {
      const tradeId = event.target.dataset.tradeId;
      if (!tradeId) return;

      if (confirm(`¿Estás seguro de que quieres eliminar el trade #${tradeId}?`)) {
        try {
          const response = await fetch(`/api/trade/${tradeId}`, {
            method: 'DELETE',
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Error ${response.status}`);
          }

          showToast(`Trade #${tradeId} eliminado exitosamente.`, 'success');
          // Recargar la página para actualizar el historial
          location.reload();
        } catch (error) {
          console.error('Error al eliminar trade:', error);
          showToast(`Error al eliminar trade #${tradeId}: ${error.message}`, 'error');
        }
      }
    }

    // Manejar edición de trade (mostrar formulario)
    if (event.target.classList.contains('btn-edit-trade')) {
      const tradeId = event.target.dataset.tradeId;
      if (!tradeId) return;

      // Encontrar la fila del trade
      const tradeRow = event.target.closest('tr');
      if (!tradeRow) return;

      // Obtener datos actuales del trade (simplificado, idealmente se haría una llamada a la API)
      const currentAction = tradeRow.children[1].textContent.trim().toLowerCase();
      const currentUsdAmount = parseFloat(tradeRow.children[2].textContent.trim());
      const currentRate = parseFloat(tradeRow.children[3].textContent.trim());
      // const currentFees = ... (no visible en la tabla, se necesitaría otra forma de obtenerlo) 

      // Crear un formulario de edición simple (o usar un modal)
      const editFormHtml = `
      <tr class="edit-form-row">
        <td colspan="6">
          <div style="padding: 1rem; background: var(--background-tertiary); border-radius: 8px; margin-top: 0.5rem;">
            <h4>Editar Trade #${tradeId}</h4>
            <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
              <select id="edit-action-${tradeId}" style="flex: 1;">
                <option value="buy" ${currentAction === 'buy' ? 'selected' : ''}>COMPRAR</option>
                <option value="sell" ${currentAction === 'sell' ? 'selected' : ''}>VENDER</option>
              </select>
              <input type="number" id="edit-usd-amount-${tradeId}" value="${currentUsdAmount}" placeholder="Monto USD" style="flex: 1;">
              <input type="number" id="edit-rate-${tradeId}" value="${currentRate}" placeholder="Tasa" style="flex: 1;">
              <input type="number" id="edit-fees-${tradeId}" value="0" placeholder="Comisiones" style="flex: 1;"> <!-- Fees hardcoded for now -->
            </div>
            <button class="btn-save-trade mini-btn" data-trade-id="${tradeId}">💾 Guardar</button>
            <button class="btn-cancel-edit mini-btn">❌ Cancelar</button>
          </div>
        </td>
      </tr>
    `;

    // Insertar formulario después de la fila actual
    tradeRow.insertAdjacentHTML('afterend', editFormHtml);
    tradeRow.style.display = 'none'; // Ocultar fila original
  }

  // Manejar guardar edición
  if (event.target.classList.contains('btn-save-trade')) {
    const tradeId = event.target.dataset.tradeId;
    if (!tradeId) return;

    const action = document.getElementById(`edit-action-${tradeId}`).value;
    const usd_amount = parseFloat(document.getElementById(`edit-usd-amount-${tradeId}`).value);
    const rate = parseFloat(document.getElementById(`edit-rate-${tradeId}`).value);
    const fees = parseFloat(document.getElementById(`edit-fees-${tradeId}`).value);

    try {
      const response = await fetch(`/api/trade/${tradeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, usd_amount, rate, fees }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error ${response.status}`);
      }

      showToast(`Trade #${tradeId} actualizado exitosamente.`, 'success');
      location.reload(); // Recargar para ver cambios
    } catch (error) {
      console.error('Error al actualizar trade:', error);
      showToast(`Error al actualizar trade #${tradeId}: ${error.message}`, 'error');
    }
  }

  // Manejar cancelar edición
  if (event.target.classList.contains('btn-cancel-edit')) {
    const editFormRow = event.target.closest('.edit-form-row');
    if (editFormRow) {
      editFormRow.previousElementSibling.style.display = ''; // Mostrar fila original
      editFormRow.remove();
    }
  }
  });

  // ============================================================================
  // Inicialización
  // ============================================================================

  // Iniciar actualizador de tiempo
  startTimeAgoUpdater();

  // Iniciar auto-refresh
  startAutoRefresh();

  // Renderizar gráfico inicial
  console.log('🚀 Inicializando dashboard - llamando renderChart(24)');
  const canvasElement = document.getElementById('trend-chart');
  console.log('Canvas element found:', !!canvasElement);

  if (canvasElement) {
    renderChart(24).then(() => {
      console.log('✅ Gráfico de tendencia cargado inicialmente');
    }).catch(error => {
      console.error('❌ Error al cargar gráfico inicial:', error);
    });
  } else {
    console.error('❌ Canvas #trend-chart no encontrado en inicialización');
  }
  
  // Capturar filas de proveedores para filtros
  if (providerTableBody) {
    captureProviderRows();
  }
  
  // Recarga completa de la página cada 300 segundos
  const fullPageReloadInterval = setInterval(() => {
    // Solo recargar si la página está visible para no molestar en segundo plano
    if (document.visibilityState === 'visible') {
      showToast('Recargando página completa...', 'info');
      setTimeout(() => location.reload(), 500);
    }
  }, 300000); // 300 segundos

  // Limpiar intervals al salir
  window.addEventListener('beforeunload', () => {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    if (timeAgoInterval) clearInterval(timeAgoInterval);
    if (liveUpdateInterval) clearInterval(liveUpdateInterval);
    if (trendChart) trendChart.destroy();
    if (fullPageReloadInterval) clearInterval(fullPageReloadInterval);
  });
  
  // Pausar auto-refresh cuando la pestaña no está visible
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    } else {
      startAutoRefresh();
    }
  });
});

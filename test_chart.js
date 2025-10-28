// Script de prueba para verificar las funciones del gráfico
const fs = require('fs');

// Leer el archivo dashboard.js
const jsContent = fs.readFileSync('cambio_dollar/src/cambio_dollar/web/static/js/dashboard.js', 'utf8');

// Extraer las funciones críticas
const functionsToTest = [
  'fmtNumber',
  'shortText', 
  'escapeHtml',
  'updateTimeAgo',
  'processChartData',
  'calculateStats',
  'loadChartData'
];

console.log('=== VERIFICACIÓN DE FUNCIONES ===');

functionsToTest.forEach(funcName => {
  const funcRegex = new RegExp(`function ${funcName}\\([^)]*\\)`, 'g');
  const match = jsContent.match(funcRegex);
  if (match) {
    console.log(`✅ Función ${funcName} encontrada`);
  } else {
    console.log(`❌ Función ${funcName} NO encontrada`);
  }
});

// Verificar que renderChart tiene el contenido esperado
const renderChartMatch = jsContent.match(/async function renderChart\([^)]*\) \{([\s\S]*?)\}/);
if (renderChartMatch) {
  const renderChartContent = renderChartMatch[1];
  
  const checks = [
    { name: 'Verificación de canvas', pattern: /canvas.*no encontrado/ },
    { name: 'Verificación de Chart.js', pattern: /Chart\.js.*no está cargado/ },
    { name: 'Gráfico de prueba', pattern: /Creando gráfico de prueba/ },
    { name: 'Carga de datos reales', pattern: /Cargando datos reales/ },
    { name: 'Actualización con datos reales', pattern: /Actualizando gráfico con datos reales/ }
  ];
  
  checks.forEach(check => {
    if (renderChartContent.match(check.pattern)) {
      console.log(`✅ ${check.name} presente en renderChart`);
    } else {
      console.log(`❌ ${check.name} NO encontrado en renderChart`);
    }
  });
  
  console.log(`\nLongitud del contenido de renderChart: ${renderChartContent.length} caracteres`);
} else {
  console.log('❌ Función renderChart no encontrada');
}

console.log('\n=== PRUEBA DE FUNCIONES DE UTILIDAD ===');

// Probar fmtNumber (simular la función)
function fmtNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '—';
  return Number(value).toFixed(decimals);
}

console.log('fmtNumber(63.45):', fmtNumber(63.45));
console.log('fmtNumber(null):', fmtNumber(null));

// Probar updateTimeAgo (simular la función)
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

const recentTime = new Date(Date.now() - 5 * 60 * 1000); // 5 minutos atrás
const oldTime = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000); // 2 días atrás

console.log('updateTimeAgo(recent):', updateTimeAgo(recentTime));
console.log('updateTimeAgo(old):', updateTimeAgo(oldTime));
console.log('updateTimeAgo(null):', updateTimeAgo(null));

console.log('\n=== FIN DE PRUEBA ===');

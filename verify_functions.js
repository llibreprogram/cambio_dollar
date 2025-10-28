const fs = require('fs');
const js = fs.readFileSync('cambio_dollar/src/cambio_dollar/web/static/js/dashboard.js', 'utf8');

const loadChartDataMatch = js.match(/async function loadChartData\([^)]*\) \{([\s\S]*?)\}/);
const processChartDataMatch = js.match(/function processChartData\([^)]*\) \{([\s\S]*?)\}/);
const calculateStatsMatch = js.match(/function calculateStats\([^)]*\) \{([\s\S]*?)\}/);

console.log('=== VERIFICACIÓN DE FUNCIONES ===');
console.log('loadChartData existe:', !!loadChartDataMatch);
console.log('processChartData existe:', !!processChartDataMatch);
console.log('calculateStats existe:', !!calculateStatsMatch);

if (loadChartDataMatch) {
  console.log('loadChartData longitud:', loadChartDataMatch[1].length, 'caracteres');
}
if (processChartDataMatch) {
  console.log('processChartData longitud:', processChartDataMatch[1].length, 'caracteres');
}
if (calculateStatsMatch) {
  console.log('calculateStats longitud:', calculateStatsMatch[1].length, 'caracteres');
}
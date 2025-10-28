#!/usr/bin/env node

// Script de prueba para verificar Chart.js y el canvas
const puppeteer = require('puppeteer');

async function testChartRendering() {
  console.log('🚀 Iniciando prueba de renderizado de gráfico...');

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();
    await page.goto('http://localhost:8000', { waitUntil: 'networkidle2' });

    // Esperar a que se cargue Chart.js
    await page.waitForFunction(() => typeof Chart !== 'undefined', { timeout: 10000 });

    // Verificar que el canvas existe
    const canvasExists = await page.$('#trend-chart');
    console.log('✅ Canvas encontrado:', !!canvasExists);

    // Verificar que Chart.js está disponible
    const chartAvailable = await page.evaluate(() => typeof Chart !== 'undefined');
    console.log('✅ Chart.js disponible:', chartAvailable);

    // Verificar que dashboard.js se cargó
    const dashboardLoaded = await page.evaluate(() => typeof renderChart !== 'undefined');
    console.log('✅ dashboard.js cargado:', dashboardLoaded);

    // Intentar ejecutar renderChart manualmente
    console.log('🔄 Intentando ejecutar renderChart...');
    const result = await page.evaluate(async () => {
      try {
        if (typeof renderChart === 'function') {
          await renderChart();
          return '✅ renderChart ejecutado sin errores';
        } else {
          return '❌ renderChart no es una función';
        }
      } catch (error) {
        return '❌ Error ejecutando renderChart: ' + error.message;
      }
    });

    console.log('Resultado:', result);

    // Verificar si hay errores en la consola
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.waitForTimeout(2000); // Esperar 2 segundos

    if (errors.length > 0) {
      console.log('❌ Errores en consola:');
      errors.forEach(error => console.log('  -', error));
    } else {
      console.log('✅ No hay errores en consola');
    }

    // Tomar screenshot
    await page.screenshot({ path: 'chart_test_screenshot.png', fullPage: true });
    console.log('📸 Screenshot guardado como chart_test_screenshot.png');

  } catch (error) {
    console.error('❌ Error en la prueba:', error.message);
  } finally {
    await browser.close();
  }
}

testChartRendering();
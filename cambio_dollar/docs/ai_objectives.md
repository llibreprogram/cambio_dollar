# Objetivos medibles para IA de Cambio Dollar

## 1. KPIs Estratégicos

- **Margen esperado por trade (Expected Profit)**  
  - *Meta inicial*: superar en un 20% la ganancia estimada vs. la heurística actual en backtests de 3 meses.  
  - *Meta avanzada*: mantener delta ≥ 35% con drawdown controlado.
- **Drawdown máximo (Max DD)**  
  - *Meta inicial*: ≤ 12% en simulaciones con fees y slippage.  
  - *Meta avanzada*: ≤ 8% con riesgo modelado.
- **Hit Rate por acción (BUY/SELL/HOLD)**  
  - *Meta inicial*: ≥ 55% de aciertos netos por clase.  
  - *Meta avanzada*: ≥ 65%, manteniendo rebalance en clases (no sesgos extremos).
- **Retorno anualizado (Annualized Return)**  
  - *Meta inicial*: batir baseline “HOLD” o “Spread promedio” en +15%.  
  - *Meta avanzada*: ≥ +25% con varianza estable.
- **Latencia de decisión**  
  - *Meta*: respuesta < 2 segundos por recomendación (80 percentil).
- **Cobertura de datos**  
  - *Meta inicial*: 90% de proveedores clave con actualizaciones en <15 min.  
  - *Meta avanzada*: ≥ 95% con monitoreo automático de caídas.

## 2. Marcos de evaluación

- **Backtesting Rolling Window**  
  - Ventanas de 30, 60 y 90 días; recalibrar modelo y medir KPIs.  
  - Comparar contra heurística actual, baseline aleatorio y estrategias de spread fijo.
- **Validación en tiempo real (paper trading)**  
  - Ejecutar recomendaciones simuladas a diario, registrar resultados vs. mercado real.  
  - Consolidar en reporte semanal.
- **Monitoreo post-despliegue**  
  - Trackear drift de features (KS test) y performance vs. expectativas.  
  - Alertas si Expected Profit cae >15% o si Drawdown supera meta.

## 3. Criterios de éxito por fase

| Fase | Hito | Criterio | Controles |
|------|------|----------|-----------|
| MVP | Modelo supervisado baseline | ≥20% mejora Expected Profit en backtest 90 días; Max DD ≤12% | Informe EDA, scripts reproducibles |
| Beta | Integración con pipeline y API | Paper trading 4 semanas con KPIs dentro de meta | Dashboard de métricas en web/app |
| Producción | Despliegue con retraining | KPIs avanzados cumplidos; alertas activas; rollback definido | Documentación + runbooks |

## 4. Riesgos y mitigaciones

- **Datos insuficientes**: crear dataset sintético/backtests, incorporar fuentes externas.  
- **Sesgos de mercado**: usar cross-validation temporal y stress tests (picos de volatilidad).  
- **Bloqueo operacional**: mantener heurística actual como fallback en `StrategyEngine`.  
- **Deriva del modelo**: programar retraining automático y monitoreo de drift.

## 5. Próximos pasos

1. Implementar tracking de KPIs actuales (guardar métricas en BD/notebooks).  
2. Comparar heurística vs. baseline aleatorio para establecer punto de partida.  
3. Pasar a diseño del pipeline de datos según objetivos definidos.

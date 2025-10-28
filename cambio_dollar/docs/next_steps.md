# Próximas implementaciones

## 1. Esquema y migraciones
- Ampliar `repository.py` con tablas:
  - `feature_store` (features enriquecidos).
  - `labels_performance` (etiquetas para entrenamiento).
  - `external_macro` (datos macro externos).
  - `model_evaluations` (resultados de backtesting/experimentos).
- Crear migración SQL o script que modifique la base SQLite existente.
- La tabla `anomaly_events` fue creada durante la Fase B y ya recibe registros en tiempo real.

## 2. Scripts ETL
- `scripts/fetch_macro.py`: descarga indicadores (DXY, tasas, etc.) y los almacena.
- `scripts/build_dataset.py`: combina snapshots + features + macro + etiquetas → dataset maestro.
- Validaciones con Pandera/Great Expectations.

## 3. Setup ML
- Actualizar `pyproject.toml` con dependencias ML (mlflow, scikit-learn, lightgbm, pandera, polars, etc.).
- Añadir tareas al `Makefile`: `make build-dataset`, `make train-baseline`, `make mlflow-ui`.
- Crear `scripts/train_model.py` y `scripts/evaluate_model.py` (baseline heurística vs. modelo supervisado).

## 4. Integración con dashboard/API
- Endpoint para mostrar estado de modelos (versión, métricas recientes).
- Visualizaciones en dashboard: gráfico de KPIs y resultados de backtesting.

## 5. Roadmap inmediato

1. ✅ Registrar eventos de anomalía (`anomaly_events`) y conectar detectores en tiempo real.
2. ⏳ Calcular error vs. consenso en los rollups (`provider_metrics`) y derivar pesos dinámicos.
3. ⏳ Implementar monitores adicionales (EWMA/CUSUM) y preparar tabla `drift_events`.
4. ⏳ Desarrollar ETL macro + dataset maestro.
5. ⏳ Configurar dependencias ML y scripts de entrenamiento.
6. ⏳ Integrar resultados en dashboard/API con visualizaciones de confiabilidad y anomalías.

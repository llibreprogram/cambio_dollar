# Entorno de experimentación de IA · Cambio Dollar

## 1. Objetivos
- Permitir experimentos reproducibles sobre el dataset maestro.
- Versionar modelos, parámetros, métricas y artefactos.
- Facilitar colaboración entre data scientists e ingenieros.
- Integrarse con el pipeline de datos y el motor de inferencia.

## 2. Herramientas recomendadas

| Propósito | Herramienta | Uso propuesto |
|-----------|-------------|---------------|
| Tracking de experimentos | **MLflow** | Registrar runs, parámetros, métricas, artefactos. Servir GUI vía `mlflow ui`. |
| Orquestación ligera | **Make + scripts Python** (fase 1) | Automatizar pasos (`make build-dataset`, `make train-baseline`). |
| Notebooks interactivos | **Jupyter** (VSCode o `.ipynb`) | EDA, prototipos rápidos. Guardar en `notebooks/`. |
| Validación de datos | **Pandera** / **Great Expectations** | Tests sobre dataset antes de entrenar. |
| Feature engineering | **pandas / polars** | Transformaciones y agregaciones. |
| Modelado inicial | **scikit-learn**, **LightGBM**, **XGBoost** | Modelos baseline y gradient boosting. |
| Deep Learning futuro | **PyTorch** o **TensorFlow** | Para LSTM/TFT cuando el dataset lo permita. |
| Backtesting | Módulo interno (`analytics.py`) + scripts | Simulaciones comparativas con heurística. |

## 3. Estructura propuesta de directorios

```
/ai/
  experiments/
    2025-10-08_baseline_lightgbm/
      config.yaml           # parámetros del experimento
      metrics.json          # métricas finales
      model.pkl             # artefacto serializado
      feature_importance.png
  datasets/
    processed/
      dataset_20251008.parquet
    interim/
      features_raw.parquet
  notebooks/
    2025-10-08_eda_notebook.ipynb
  scripts/
    build_dataset.py
    train_model.py
    evaluate_model.py
```

> Nota: podemos usar `mlflow` para almacenar artefactos en lugar de carpetas manuales; la estructura sirve de guía inicial.

## 4. Flujo de trabajo

1. **Preparar datos**
   - Ejecutar `scripts/build_dataset.py` (usa `data_pipeline.md` como blueprint).
   - Validar dataset con Pandera/Great Expectations.
   - Registrar versión en MLflow (`mlflow.log_artifact`).

2. **Experimentar/Entrenar**
   - Configurar parámetros en `config.yaml` o CLI.
   - Correr `scripts/train_model.py --config=config.yaml`.
   - Loggear en MLflow: métricas (MAPE, Expected Profit, Max DD), parámetros, tiempo de entrenamiento.
   - Guardar artefactos (modelo, gráficas) en MLflow y en `/ai/experiments/`.

3. **Evaluar/Backtest**
   - `scripts/evaluate_model.py` ejecuta backtesting y genera reportes.
   - Guardar resultados en MLflow + tabla `model_evaluations` (opcional).

4. **Promover a producción**
   - Seleccionar run con métricas ≥ objetivos.
   - Registrar modelo en MLflow Model Registry (o guardar artefacto en `models/`).
   - Actualizar `StrategyEngine` para cargar versión aprobada.

5. **Reentrenamiento automático**
   - Crear tarea (`make retrain`) que: reconstruya dataset → entrene → evalúe → promocione si pasa umbral.
   - Integrar con scheduler o CI/CD (GitHub Actions) para periodicidad semanal.

## 5. Configuración inicial

1. **Instalación de dependencias**
   - Añadir a `pyproject.toml` (grupo opcional `[tool.poetry.group.ml]`):
     ```
     mlflow
     scikit-learn
     lightgbm
     xgboost
     pandas
     polars
     pandera
     great-expectations
     ```
     *(Ajustar según gestor de dependencias.)*

2. **MLflow Tracking**
   - Crear archivo `.mlflow` o usar variable de entorno `MLFLOW_TRACKING_URI` (por defecto `mlruns/`).
   - Añadir `make mlflow-ui` que ejecute `mlflow ui --host 0.0.0.0 --port 5000`.

3. **Scripts base**
   - `scripts/build_dataset.py`: carga datos, genera features, exporta dataset + logs.
   - `scripts/train_model.py`: entrena modelo baseline (p.ej., LightGBM) y registra run en MLflow.
   - `scripts/evaluate_model.py`: ejecuta backtesting y guarda resultados.

4. **Notebooks estándar**
   - Plantilla para EDA (`notebooks/template_eda.ipynb`): distribución de tasas, correlaciones, heatmaps.
   - Plantilla de experimentos (`notebooks/template_experiment.ipynb`): configuración, resultados, conclusiones.

## 6. Buenas prácticas
- **Reproducibilidad**: fijar semillas (`np.random.seed`), registrar versiones de librerías.
- **Documentación**: cada experimento debe incluir objetivo, hipótesis, resultados y próximos pasos.
- **Colaboración**: usar PRs para scripts/notebooks clave; evitar notebooks sin limpieza (ejecutar `nbstripout`).
- **Seguridad**: guardar credenciales API en `.env` y no en notebooks.

## 7. Próximos pasos
1. Actualizar dependencias e instalar MLflow y librerías ML básicas.
2. Crear scripts iniciales `build_dataset.py` y `train_model.py` (baseline heurística vs. modelo simple).
3. Configurar `Makefile` con tareas (`make build-dataset`, `make train-baseline`, `make mlflow-ui`).
4. Preparar notebooks base para EDA y experimentos.

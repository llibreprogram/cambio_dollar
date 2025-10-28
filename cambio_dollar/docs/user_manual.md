# Manual de usuario · Cambio Dollar

> **Objetivo**: guiar a cualquier persona (analista, operador o colaborador técnico) a instalar, configurar y utilizar el asistente Cambio Dollar para consultar cotizaciones USD/DOP, generar recomendaciones y operar el dashboard web.

---

## 1. Conceptos clave

- **Snapshot**: captura puntual de tasas de compra/venta por proveedor.
- **Consenso**: agregación estadística de snapshots activos para obtener tasas representativas.
- **Recomendación**: sugerencia BUY/SELL/HOLD con tasas óptimas y ganancia esperada.
- **Scheduler**: proceso que automatiza la captura periódica de mercado.
- **Dashboard web**: vista en tiempo real con consenso, proveedores, acciones rápidas y métricas.

---

## 2. Requisitos previos

| Componente | Versión recomendada | Notas |
|------------|--------------------|-------|
| Python     | 3.10 o superior    | Probado con 3.12.3. |
| SQLite     | Incluido con Python | La base vive en `data/cambio_dollar.sqlite`. |
| Git        | Opcional           | Para clonar el repositorio. |
| make       | Opcional           | Simplifica comandos (`Makefile`). |

> En entornos Windows se recomienda WSL2 o Docker. Mac/Linux funcionan de forma nativa.

---

## 3. Instalación rápida

1. **Clona o descarga** el proyecto.
2. **Crea el entorno virtual y dependencias**:

    ```bash
    make bootstrap
    ```

3. **Configura las variables por defecto** (opcional, pero recomendable):

    ```bash
    cp .env.example .env
    ```

4. **Aplica las migraciones de base de datos**:

    ```bash
    make migrate
    ```

5. **Ejecuta la suite de pruebas** para validar el entorno:

    ```bash
    make test
    ```

> Si prefieres hacerlo manualmente sin Makefile, consulta la sección [Instalación manual](../README.md#instalación-manual).

---

## 4. Configuración

Toda la configuración se define en `cambio_dollar.config.Settings` y puede sobrescribirse con variables de entorno (prefijo `CAMBIO_`). Ejemplos frecuentes:

| Propósito | Variable | Descripción | Valor por defecto |
|-----------|----------|-------------|-------------------|
| Ruta base de datos | `CAMBIO_DB_PATH` | SQLite donde se guardan snapshots y métricas. | `data/cambio_dollar.sqlite` |
| Costos por transacción | `CAMBIO_TRANSACTION_COST` | En DOP por USD. | `0.15` |
| Latencia del scheduler | `CAMBIO_SCHEDULER_INTERVAL_SECONDS` | Intervalo entre capturas automáticas. | `300` |
| Host del servidor web | `CAMBIO_SERVER_HOST` | Dirección de enlace del dashboard/API. | `127.0.0.1` (IPv4 loopback) |
| Puerto del servidor web | `CAMBIO_SERVER_PORT` | Puerto TCP del dashboard/API. | `8000` |

### Proveedores

Cada proveedor se describe en la lista `providers`. Para habilitar o ajustar uno específico:

```bash
export CAMBIO_PROVIDERS__3__ENABLED=true
export CAMBIO_PROVIDERS__3__ENDPOINT="https://tu.api.oficial/dolar"
```

> Nota: la notación con doble guion bajo (`__`) permite acceder a índices y campos dentro de la lista de proveedores según la convención de Pydantic.

### Autenticación

Algunos proveedores requieren tokens o encabezados especiales. Define las variables esperadas, por ejemplo:

```bash
export BCRD_API_KEY="tu-api-key"
export BPD_CLIENT_ID="tu-client-id"
export BPD_CLIENT_SECRET="tu-client-secret"
```

---

## 5. Flujo típico de trabajo

| Paso | Comando | Resultado |
|------|---------|-----------|
| Capturar cotizaciones | `make fetch` | Obtiene snapshots, actualiza consenso y registra métricas. |
| Revisar recomendación | `make analyze` | Muestra BUY/SELL/HOLD, tasas sugeridas y forecast diario. |
| Iniciar dashboard | `make serve` | Levanta API + panel web (`http://127.0.0.1:8000`). |
| Listar proveedores | `make providers` | Verifica estado, cobertura y notas. |
| Ejecutar scheduler | `make serve` con `CAMBIO_SCHEDULER_ENABLED=true` | Captura automática en segundo plano. |

> Todos los comandos `make` tienen su equivalente directo `cambio-dollar <subcomando>`.

---

## 6. CLI del asistente

La aplicación incluye un CLI basado en Typer. Ejecuta `cambio-dollar --help` para ver todas las opciones. Algunas de las más usadas:

### 6.1 Captura de mercado

```bash
cambio-dollar fetch --repetitions 3 --interval 60
```

- `--repetitions`: número de capturas consecutivas.
- `--interval`: pausa (segundos) entre capturas cuando son múltiples.

### 6.2 Recomendación y forecast

```bash
cambio-dollar analyze
```

Muestra la recomendación actual del motor (`StrategyEngine`), tasas sugeridas y pronóstico de utilidad diaria.

### 6.3 Proveedores

```bash
cambio-dollar providers --include-derived
```

Lista proveedores nativos y derivados (por ejemplo, bancos que comparten origen vía InfoDolar).

### 6.4 Métricas de confiabilidad

```bash
cambio-dollar provider-metrics --window-minutes 180 --dry-run
```

Calcula (o persiste) ratios de cobertura, éxito y latencias por proveedor en una ventana móvil.

### 6.5 Servidor web

```bash
cambio-dollar serve --host 0.0.0.0 --port 8080 --reload
```

- `--host` y `--port` tienen como valores por defecto `CAMBIO_SERVER_HOST`/`CAMBIO_SERVER_PORT`.
- `--reload` es ideal para desarrollo (reinicia automáticamente al detectar cambios).

> El CLI también permite registrar operaciones manuales (`cambio-dollar trade buy|sell`), revisar drift (`cambio-dollar drift`), exportar históricos, entre otros.

---

## 7. Dashboard web

- **URL predeterminada**: `http://127.0.0.1:8000/`.
- **Secciones principales**:
  - Resumen de consenso: tasas medianas y ponderadas.
  - Motor de recomendaciones: acción, confianza, spread neto y justificación.
  - Tabla de proveedores: estado, origen, tags de agregación y notas.
  - Acciones rápidas: botón “Capturar ahora” y estado del scheduler.

### 7.1 Captura manual desde el panel

Haz clic en “Capturar ahora” para solicitar una nueva captura. El backend ejecuta `MarketDataService.capture_market()` y actualiza la vista.

### 7.2 Acceso remoto (LAN)

```bash
export CAMBIO_SERVER_HOST=0.0.0.0
export CAMBIO_SERVER_PORT=8080
make serve
```

Desde otra máquina en la misma red visita `http://IP_DEL_SERVIDOR:8080/`.

### 7.3 Acceso remoto (Internet)

1. Configura el router/NAT para redirigir el puerto público hacia el servidor.
2. Utiliza un dominio o DNS dinámico para mapear la IP pública.
3. Protege el acceso con un proxy inverso (HTTPS + autenticación).
4. Ajusta `CAMBIO_SERVER_HOST="0.0.0.0"` y el puerto interno según el mapeo.

> Como alternativa segura, puedes crear un túnel (SSH, ngrok, Cloudflare Tunnel, Tailscale, etc.) sin abrir puertos públicos.

---

## 8. Scheduler automático

Para activar el scheduler embebido que captura mercado de forma periódica:

```bash
export CAMBIO_SCHEDULER_ENABLED=true
export CAMBIO_SCHEDULER_INTERVAL_SECONDS=300  # cada 5 minutos
make serve
```

- El estado del scheduler se expone en `GET /api/scheduler` y en el panel web.
- Durante el scheduler, las capturas se registran en la misma base SQLite y disparan la generación de recomendaciones.

---

## 9. Gestión de datos

| Tarea | Comando/acción |
|-------|----------------|
| Ver últimos snapshots | `sqlite3 data/cambio_dollar.sqlite 'SELECT * FROM rate_snapshots ORDER BY timestamp DESC LIMIT 10;'` |
| Respaldar la base | Copia `data/cambio_dollar.sqlite` o usa `sqlite3 .dump`. |
| Resetear datos | Borra el archivo SQLite y vuelve a ejecutar `make migrate` (perderás historiales). |

> Se incluye `data/sample_rates.csv` para demos o pruebas rápidas.

---

## 10. Pruebas y mantenimiento

- **Pruebas unitarias**: `make test` o `.venv/bin/python -m pytest`.
- **Formato y linting (si está configurado)**: consulta `pyproject.toml` para herramientas como Ruff.
- **Actualizaciones**: al cambiar dependencias, ejecuta `make bootstrap` nuevamente.

---

## 11. Solución de problemas

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| `Connection refused` al acceder al dashboard desde otra máquina | El servidor escucha solo en loopback o el firewall bloquea el puerto. | Usa `CAMBIO_SERVER_HOST=0.0.0.0` y abre el puerto (`sudo ufw allow <puerto>/tcp`). |
| OverflowError en recomendación | Momentum extremo sin guardas (histórico). | Actualizaciones recientes incluyen un sigmoid estable. Asegúrate de tener la versión más nueva. |
| Proveedor falla por autenticación | Variables de entorno no definidas. | Revisa `ProviderSettings.auth_headers` y exporta las claves necesarias. |
| Scheduler no se activa | `CAMBIO_SCHEDULER_ENABLED` en `false` o intervalos < 60 s. | Establece `CAMBIO_SCHEDULER_ENABLED=true` y usa un intervalo ≥ 60. |
| `sqlite3.OperationalError: database is locked` | Múltiples procesos accediendo simultáneamente. | Evita correr CLI y scheduler sobre la misma base en modo escritura intensiva. |

---

## 12. Apéndice · Comandos útiles

| Acción | Comando |
|--------|---------|
| Capturar mercado cada minuto (3 veces) | `cambio-dollar fetch -r 3 -i 60` |
| Ver intervención del drift monitor | `cambio-dollar drift` |
| Registrar una operación | `cambio-dollar trade sell 500 --rate 58.4 --fees 50` |
| Exportar métricas de proveedores | `cambio-dollar provider-metrics --window-minutes 60` |
| Ejecutar dashboard con recarga | `cambio-dollar serve --reload` |
| Ejecutar dashboard con túnel SSH | `ssh -L 8080:localhost:8080 usuario@servidor` + `http://localhost:8080` |

---

## 13. Recursos adicionales

- [`docs/data_pipeline.md`](./data_pipeline.md): diseño del pipeline de datos y próximos pasos analíticos.
- `docs/ai_objectives.md`: objetivos estratégicos de IA para el proyecto.
- `docs/ai_experimentation.md`: experimentos planeados y backlog técnico.
- `docs/next_steps.md`: hoja de ruta general.

> Mantén este manual junto al repositorio. A medida que se agreguen nuevas funcionalidades (alertas, modelos ML, integraciones externas) recuerda actualizar las secciones correspondientes.

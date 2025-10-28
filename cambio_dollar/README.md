# Cambio Dollar

Asistente inteligente en Python para comprar y vender dólares estadounidenses (USD) frente al peso dominicano (DOP) con un enfoque basado en datos.

## Características clave

- Ingesta multi-origen de cotizaciones USD/DOP con construcción de consenso y validación de discrepancias.
- Configuración declarativa vía `pydantic-settings`, incluyendo umbrales de divergencia por proveedor.
- Genera recomendaciones de compra/venta basadas en tendencia, spreads y volatilidad.
- Registra operaciones reales o simuladas y calcula la ganancia por operación.
- Proyecta la utilidad esperada al cierre del día con un modelo de regresión lineal simple.
- Notebook interactivo con Plotly para monitoreo en tiempo real y análisis histórico.
- API REST + dashboard web (FastAPI + Jinja2) con disparo manual de capturas y estado del scheduler.
- Monitor de drift basado en EWMA + CUSUM con persistencia y exposición vía CLI, API y dashboard.

## Inicio rápido

```bash
make bootstrap
cp .env.example .env  # opcional, ajusta valores si lo necesitas
make migrate          # aplica migraciones Alembic a la base local
make serve
```

- Consulta `docs/local_dev_setup.md` para una guía paso a paso con prerequisitos, configuración de variables de entorno y comandos frecuentes.
- Lee `docs/drift_monitoring.md` para configurar umbrales y entender el pipeline de detección de drift.

- `make bootstrap` crea el entorno virtual en `.venv` e instala todas las dependencias (incluidas las de desarrollo).
- `make migrate` aplica la migración base (`0001_initial_schema`) y cualquier revisión pendiente sobre `CAMBIO_DB_PATH`.
- `make serve` arranca la API REST y el dashboard Jinja/HTMX utilizando `CAMBIO_SERVER_HOST`/`CAMBIO_SERVER_PORT` (por defecto `127.0.0.1:8000`).
- `make analyze` genera la recomendación IA con tasas sugeridas y proyección de utilidades.
- Puedes ejecutar cualquier comando del asistente mediante `make <tarea>` (por ejemplo `make fetch`, `make analyze`).

## Instalación manual

1. Crea y activa un entorno virtual de Python 3.10+.
2. Instala el paquete en modo editable junto con las dependencias de desarrollo:

```bash
python -m pip install -e .[dev]
```

3. (Opcional) Crea un archivo `.env` (puedes copiar `cp .env.example .env`) para sobreescribir valores de configuración, por ejemplo:

```
CAMBIO_PRIMARY_ENDPOINT=https://api.exchangerate.host/latest?base=USD&symbols=DOP
CAMBIO_TRANSACTION_COST=0.10
```

## Uso rápido del CLI

```bash
make fetch                       # Captura datos y consolida consenso
make compare                     # Compara spreads y coerencia entre bancos
make providers                   # Lista y valida la configuración activa
make analyze                     # Recomendación IA + forecast diario
make forecast                    # Calcula la utilidad proyectada al cierre
make drift                       # Lista los eventos de drift detectados
cambio-dollar drift              # Alternativa directa sin Makefile
cambio-dollar trade sell 500 --rate 58.4 --fees 50
make history                     # Muestra últimas operaciones
make serve                       # Inicia la API y el dashboard web (usa CAMBIO_SERVER_HOST/PORT)
```

> ¿Prefieres usar directamente el CLI? Todos los comandos siguen disponibles como `cambio-dollar ...` dentro de tu entorno virtual.

Todos los resultados se muestran con tablas enriquecidas en la terminal. Los datos se almacenan en `data/cambio_dollar.sqlite` por defecto.

### Inteligencia de mercado integrada

- **Recomendación IA**: el motor cruza spreads, momentum y volatilidad para sugerir BUY/SELL/HOLD, indicar tasas competitivas y estimar la ganancia neta para el bloque estándar (`CAMBIO_TRADING_UNITS`). Cada ejecución se guarda en la tabla `strategy_recommendations` para análisis posterior.
- **Proyección diaria**: junto con la recomendación se proyecta la utilidad esperada al cierre del día (mejor/peor caso y banda de confianza).
- **Historial trazable**: tanto la API (`/api/recommendation`) como el dashboard muestran el timeline de decisiones y su ventaja frente al mercado promedio.

### Dashboard en tiempo real

El notebook `notebooks/monitor_mercado.ipynb` ofrece visualizaciones interactivas con Plotly:

- Serie histórica de tasas de compra y venta por proveedor.
- Consenso actual con banderas de anomalías.
- Funciones auxiliares para capturar nuevos snapshots y añadirlos al panel sin reiniciar el kernel.

Ejecuta el notebook con Jupyter o VS Code y adapta el intervalo de actualización según tus necesidades.

### API web y panel automático

El comando `cambio-dollar serve` levanta un servidor FastAPI con endpoints JSON y un panel
minimalista en `http://localhost:8000/`.

- **Endpoints principales**
	- `GET /api/consensus`: consenso más reciente.
	- `GET /api/snapshots?minutes=180`: historial filtrado.
	- `GET /api/providers`: estado de cada proveedor configurado.
	- `GET /api/recommendation`: última recomendación del motor con tasas sugeridas.
	- `GET /api/forecast`: proyección de ganancia al cierre.
	- `POST /api/capture`: fuerza una captura (se ejecuta en segundo plano).
	- `GET /api/scheduler`: métricas del scheduler.
- **Scheduler automático**: deshabilitado por defecto para evitar llamadas involuntarias. Actívalo con:

	```bash
	export CAMBIO_SCHEDULER_ENABLED=true
	export CAMBIO_SCHEDULER_INTERVAL_SECONDS=300  # opcional
	cambio-dollar serve
	```

	La captura se ejecutará con la frecuencia configurada; los resultados se almacenan en la misma base
	SQLite utilizada por el CLI.
- El panel HTML muestra consenso, proveedores y snapshots recientes; incluye un botón “Capturar ahora”
	que llama al endpoint `/api/capture`.

#### Exponer el dashboard a otras máquinas

1. Cambia el host a `0.0.0.0` para escuchar todas las interfaces:

	```bash
	export CAMBIO_SERVER_HOST=0.0.0.0
	# Opcional: ajusta el puerto si 8000 está ocupado
	export CAMBIO_SERVER_PORT=8080
	make serve
	```

	También puedes usar directamente los flags del comando:

	```bash
	cambio-dollar serve --host 0.0.0.0 --port 8080
	```

2. Abre el puerto elegido en tu firewall/sistema operativo. En Ubuntu con UFW, por ejemplo:

	```bash
	sudo ufw allow 8080/tcp
	```

3. Desde otra máquina en la red (o a través de Internet tras configurar NAT), accede usando la IP del servidor: `http://IP_DEL_SERVIDOR:8080/`.

> **Seguridad:** expón el servicio sólo en redes confiables o detrás de un proxy con autenticación. Configura HTTPS si planeas servirlo públicamente en Internet.

##### Acceso desde fuera de tu red local (Internet)

Si la persona está en otra red o fuera de tu LAN:

1. **Configura el router/NAT** para redirigir el puerto público hacia tu servidor (port forwarding). Ejemplo: redirige `TCP 8443` en el router → `8080` en la máquina que ejecuta `cambio-dollar`.
2. **Usa un dominio o DNS dinámico** (DynDNS, DuckDNS, etc.) para evitar depender de la IP pública dinámica.
3. **Protege el servicio** con un proxy inverso (Nginx, Caddy, Traefik) que gestione HTTPS (Let's Encrypt) y, preferiblemente, autenticación básica u OIDC.
4. Ajusta `CAMBIO_SERVER_HOST=0.0.0.0` y el puerto interno para que coincida con el mapeo realizado en tu router.

> En entornos corporativos, puede requerirse coordinar con el área de redes para abrir puertos en firewalls perimetrales.

##### Alternativa segura sin abrir puertos

Si no quieres exponer el servidor directamente, considera:

- **Túnel SSH**: la máquina remota ejecuta

	```bash
	ssh -L 8080:localhost:8080 usuario@tu-servidor
	```

	y accede a `http://localhost:8080`. Necesitas acceso SSH al servidor y `Make serve` corriendo localmente.
- **Servicios de túnel gestionado** (Cloudflare Tunnel, ngrok, Tailscale Funnel, etc.) que crean un enlace seguro temporal o permanente sin modificar el router.

> **Nota:** si habilitas proveedores que requieren autenticación (por ejemplo Banco Popular) asegúrate
> de definir sus variables (`BPD_CLIENT_ID`, `BPD_CLIENT_SECRET`). Los proveedores basados en scraping
> como InfoDolar permanecen deshabilitados por defecto.

## Pruebas

Ejecuta la suite de pruebas con:

```bash
make test
```

También puedes ejecutar `python -m pytest` dentro del entorno virtual si prefieres interactuar directamente con `pytest`. Se incluye el archivo `data/sample_rates.csv` para poblar la base de datos durante pruebas o demos.

### Ajustes de configuración

La configuración por defecto vive en `cambio_dollar.config.Settings`. Puedes sobreescribir valores con variables de entorno (Pydantic utiliza la notación doble guion bajo para listas). Ejemplo:

```
CAMBIO_PROVIDERS__0__NAME=Banreservas
CAMBIO_PROVIDERS__0__ENDPOINT=https://tu.api.oficial/dolar
CAMBIO_PROVIDERS__0__BUY_PATH=data.compra
CAMBIO_PROVIDERS__0__SELL_PATH=data.venta
CAMBIO_DIVERGENCE_THRESHOLD=0.75
CAMBIO_LOG_LEVEL=INFO
BCRD_API_KEY=tu-api-key
```

Esto permite conectar APIs oficiales dominicanas y ajustar los umbrales de validación sin modificar el código.

Los conectores configurados con `max_retries` y `backoff_seconds` realizan reintentos automáticos con backoff exponencial cuando reciben códigos `429`, `500`, `503`, entre otros definidos en `retry_status_codes`, o ante timeouts momentáneos.

### Migraciones de base de datos

El esquema SQLite se gestiona con Alembic:

- `make migrate` aplica las migraciones pendientes usando la ruta definida en `CAMBIO_DB_PATH`.
- `make revision message="descripcion"` crea una nueva migración en `src/cambio_dollar/migrations/versions/`.

Consulta `docs/database_migrations.md` para ejemplos adicionales (autogeneración, resets y CI).

### Banco Central RD (API v2)

Disponible en el API Gateway oficial del Banco Central via suscripción. Para activarlo:

```
export BCRD_API_KEY="tu-subscription-key"
export CAMBIO_PROVIDERS__2__ENABLED=true
```

El conector solicita el último valor de la serie USD/DOP y deriva compra/venta a partir del payload JSON publicado.

### Banco Popular Dominicano (API oficial)

El proyecto incluye la configuración del endpoint sandbox de Banco Popular (`/consultaTasa`).
Para activarlo necesitas solicitar credenciales en el portal de desarrolladores y definir:

```
export BPD_CLIENT_ID="tu-client-id"
export BPD_CLIENT_SECRET="tu-client-secret"
export CAMBIO_PROVIDERS__3__ENABLED=true
```

El conector generará el token OAuth2 automáticamente y enviará el encabezado
`X-IBM-Client-Id`. La API devuelve compra y venta para USD y EUR; el asistente
selecciona la fila de USD y calcula el spread a partir de esos valores.

### Proveedor de remesas (Remesas Caribe)

Puedes habilitar conectores de remesas u otros agregadores compatibles que sigan el esquema `data.buy_rate`/`data.sell_rate`:

```
export CAMBIO_PROVIDERS__5__ENABLED=true
```

Si tu endpoint requiere autenticación adicional, aprovecha los campos `auth_headers` o `auth_token_env` para declarar los encabezados necesarios.

## Próximos pasos sugeridos

- Añadir conectores especializados para APIs oficiales (corporativas, bancos múltiples, remesadoras).
- Incorporar alertas (correo, Telegram o SMS) cuando se crucen umbrales de rentabilidad o divergencia.
- Añadir un modelo de inventario para gestionar posiciones abiertas y liquidez.
- Publicar un dashboard web (por ejemplo con FastAPI + Plotly Dash) a partir del notebook actual.
- Configurar la nueva acción de CI `ci.yml` para que ejecute linting (Ruff) y pruebas en cada push o pull request.

## Contribuciones

Aporta ideas y mejoras abriendo issues o pull requests.

# Diagnóstico y Correcciones del Sistema Cambio Dollar

**Fecha:** 2025-10-12  
**Diagnóstico realizado por:** Asistente IA

## 📊 Resumen Ejecutivo

### Estado del Scheduler ✅
- **Estado:** Funcionando correctamente
- **Configuración:** Captura cada 300 segundos (5 minutos)
- **Actividad:** 297 capturas en las últimas 24 horas
- **Última ejecución exitosa:** 2025-10-12 00:24:39
- **Tiempo de ejecución del servidor:** 1 día, 11 horas

**Conclusión:** El scheduler SÍ está capturando automáticamente según lo configurado.

---

## 🔧 Problemas Identificados

### 1. Espacios Extra en Nombres de Proveedores ⚠️

**Problema:**
Los nombres de proveedores extraídos desde InfoDolar (scraping HTML) se guardaban con espacios extra al inicio y final:
- `"  Abonap "` en lugar de `"Abonap"`
- `"  Banco Unión "` en lugar de `"Banco Unión"`
- `"  Asociación Duarte "` en lugar de `"Asociación Duarte"`

**Impacto:**
- Dashboard muestra proveedores duplicados
- Conteo incorrecto de proveedores activos (35 en lugar de ~28)
- Inconsistencias en consultas y reportes
- Problemas en cálculo de pesos dinámicos

**Solución Aplicada:**
Modificado `src/cambio_dollar/data_provider.py` (líneas 320-322) para agregar `.strip()` adicional:

```python
# Antes:
bank_name = cells[0].text(separator=" ", strip=True)

# Después:
bank_name = cells[0].text(separator=" ", strip=True).strip()
```

**Estado:** ✅ Código corregido, requiere reinicio del servidor

---

### 2. Proveedores con Datos Obsoletos 📅

**Proveedores sin actualización reciente:**
- RM, SCT, Girosol, Gamelin, Moneycorps: última actualización 2025-10-08
- Múltiples bancos vía InfoDolar: no se actualizaron desde el 8 de octubre
- Banco Popular (API directa): última actualización 2025-10-08

**Causa posible:**
- InfoDolar cambió su estructura HTML
- Proveedores inactivos en la fuente
- Problemas temporales de conexión

**Proveedores activos actualmente (4):**
1. ✅ Banreservas (API oficial)
2. ✅ Abonap (vía InfoDolar)
3. ✅ Asociación Duarte (vía InfoDolar)
4. ✅ Banco Unión (vía InfoDolar)

---

### 3. Proveedores Sin Configuración ❌

**Proveedores habilitados pero sin endpoints:**
- Capla
- Cambio Extranjero
- Asociación Romana

**Proveedores con APIs requeridas pero sin credenciales:**
- Banco Central RD: Requiere API key (servicio cambió a pago)
- Banco Central RD API v2: Falta `BCRD_API_KEY`
- Banco Popular: Falta `BPD_CLIENT_ID` y `BPD_CLIENT_SECRET`
- Remesas Caribe: Endpoint no existe (API inventada)

---

## 🛠️ Acciones Recomendadas

### Prioridad ALTA

#### 1. Reiniciar el Servidor
```bash
# En la terminal donde corre el servidor (pts/5), presiona Ctrl+C
# Luego:
make serve
# O:
.venv/bin/cambio-dollar serve --host 0.0.0.0 --port 8000
```

#### 2. Limpiar Base de Datos
```bash
# Ejecutar script de limpieza para normalizar nombres históricos:
python cleanup_provider_names.py
```

Este script actualizará todos los registros existentes con espacios extra.

---

### Prioridad MEDIA

#### 3. Desactivar Proveedores Sin Configuración

Editar `.env` o `src/cambio_dollar/config.py` para deshabilitar proveedores que no funcionan:

```bash
# Agregar a .env:
CAMBIO_PROVIDERS__6__ENABLED=false  # Capla
CAMBIO_PROVIDERS__7__ENABLED=false  # Cambio Extranjero
CAMBIO_PROVIDERS__8__ENABLED=false  # Asociación Romana
CAMBIO_PROVIDERS__5__ENABLED=false  # Remesas Caribe (API inexistente)
```

#### 4. Investigar InfoDolar

Verificar por qué muchos proveedores de InfoDolar no se actualizan:
```bash
# Descargar HTML actual y revisar estructura:
curl -s "https://www.infodolar.com.do/" > infodolar_current.html
# Revisar si cambió la estructura de la tabla
```

---

### Prioridad BAJA

#### 5. Configurar APIs Oficiales

Si tienes acceso a las credenciales:

**Banco Central RD API v2:**
```bash
# Obtener API key en: https://developers.bancentral.gov.do
export BCRD_API_KEY="tu-api-key"
```

**Banco Popular:**
```bash
# Solicitar credenciales en portal de desarrolladores
export BPD_CLIENT_ID="tu-client-id"
export BPD_CLIENT_SECRET="tu-client-secret"
```

#### 6. Agregar Nuevos Proveedores

Considerar agregar proveedores dominicanos adicionales con APIs públicas:
- Banco BHD León (si tiene API)
- Banco Caribe (si tiene API)
- Otras casas de cambio locales

---

## 📈 Métricas Actuales

### Consenso de Mercado
- **Compra:** 62.40 DOP
- **Venta:** 63.28 DOP
- **Spread:** 0.88 DOP
- **Proveedores considerados:** 4

### Actividad del Sistema
- **Capturas totales (24h):** 297
- **Promedio por hora:** ~12 capturas
- **Intervalo efectivo:** Cada 5 minutos (según configuración)
- **Tasa de éxito:** 100% (sin errores recientes)

### Servidor
- **PID:** 77645
- **Host:Puerto:** 0.0.0.0:8000
- **Uptime:** 1 día, 11 horas
- **Estado:** Activo y funcional

---

## 🎯 Verificación Post-Correcciones

Después de aplicar las correcciones, verificar:

1. **Nombres limpios en nuevas capturas:**
```bash
.venv/bin/cambio-dollar fetch
# Verificar que no aparezcan espacios extra en la salida
```

2. **Dashboard actualizado:**
- Abrir http://localhost:8000/
- Verificar que no hay duplicados
- Confirmar conteo correcto de proveedores

3. **Base de datos normalizada:**
```bash
# Verificar que todos los nombres están limpios
sqlite3 data/cambio_dollar.sqlite "SELECT DISTINCT source FROM rate_snapshots ORDER BY source"
```

4. **Scheduler funcionando:**
```bash
curl -s http://localhost:8000/api/scheduler | python3 -m json.tool
```

---

## 📝 Archivos Modificados

1. **src/cambio_dollar/data_provider.py**
   - Líneas 320-322: Agregado `.strip()` adicional para limpiar espacios
   - Líneas 350-370: Mejorado `_parse_price()` para manejar formato "$62.90 = $0.00"

2. **cleanup_provider_names.py** (NUEVO)
   - Script para normalizar nombres históricos en la BD

## 🎯 Segunda Corrección: Parser de Precios Mejorado

**Fecha:** 2025-10-12 (después de la primera corrección)

### Problema Adicional Identificado

Después de corregir los espacios extra, se detectó que solo 3-4 proveedores de InfoDolar
se estaban capturando, cuando el sitio tiene 23+ bancos disponibles.

**Causa raíz:** InfoDolar cambió el formato de sus datos para incluir la variación diaria
en el mismo campo:
- Formato antiguo: `"$62.90"`
- Formato nuevo: `"$62.90 = $0.00"` (precio + variación)

El parser antiguo intentaba extraer números de `"$62.90 = $0.00"` y obtenía `"62.90=$0.00"`
lo cual no se podía convertir a float.

### Solución Aplicada

Mejorado el método `_parse_price()` en `data_provider.py` (líneas 350-370):

```python
@staticmethod
def _parse_price(raw_text: str) -> Optional[float]:
    if not raw_text:
        return None
    # Eliminar símbolos de moneda
    cleaned = raw_text.replace("RD$", "").replace("US$", "").replace("$", "")
    # Extraer solo el primer número antes de '=' o variación
    if "=" in cleaned:
        cleaned = cleaned.split("=")[0].strip()
    # Buscar el primer número válido con regex
    match = re.search(r'(\d+[.,]\d+|\d+)', cleaned)
    if not match:
        return None
    cleaned = match.group(1)
    # Manejar formato con coma como decimal
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None
```

**Mejoras clave:**
1. Split por `=` para separar precio de variación
2. Regex `r'(\d+[.,]\d+|\d+)'` para extraer el primer número válido
3. Mejor manejo de casos edge como `"$63.10 $0.10"`

### Resultado

**Antes de la corrección:**
- 3 bancos capturados de InfoDolar
- 20+ bancos ignorados por error de parsing

**Después de la corrección:**
- ✅ 23 bancos capturados de InfoDolar
- ✅ Mejora de +20 bancos (+667%)
- ✅ Total estimado: ~27 proveedores activos (4 APIs directas + 23 InfoDolar)

**Bancos adicionales capturados:**
- Asociación Peravia de Ahorros y Préstamos
- Alaver, Motor Crédito, Banco Caribe
- Gamelin, Asociación Cibao
- Banco Lafise, Asociación La Nacional
- Asociación Popular, SCT, RM
- Girosol, Banco BHD, Banco Vimenca
- Bonanza Banco, Banesco, Moneycorps
- Banco Popular (vía InfoDolar)
- Panora Exchange
- Y más...

---

## 🔄 Próximos Pasos Sugeridos

1. ✅ Aplicar correcciones inmediatas (reiniciar servidor + limpiar BD)
2. 📊 Monitorear capturas durante 24 horas
3. 🔍 Investigar por qué algunos proveedores de InfoDolar no se actualizan
4. 🔑 Obtener API keys oficiales (Banco Central, Banco Popular)
5. 🧹 Limpiar configuración de proveedores inactivos
6. 📈 Considerar agregar proveedores adicionales

---

**Fin del Diagnóstico**


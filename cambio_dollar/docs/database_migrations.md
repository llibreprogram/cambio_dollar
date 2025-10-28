# Database Migrations

_Last updated: 2025-10-08_

Cambio Dollar usa **Alembic** para versionar el esquema SQLite. Esta guía resume los comandos disponibles y las buenas prácticas para mantener la base de datos sincronizada.

## 1. Requisitos previos

- Entorno virtual instalado (`make bootstrap`).
- Dependencias actualizadas (`pip install -e .[dev]` se ejecuta automáticamente en el objetivo `bootstrap`).
- Variable `CAMBIO_DB_PATH` apuntando al archivo SQLite deseado (por defecto `./data/cambio_dollar.sqlite`).

## 2. Aplicar migraciones

Para llevar la base de datos al último estado registrado:

```bash
make migrate
```

Esto ejecuta internamente:

```bash
python -m cambio_dollar.db_migrations upgrade
```

El script detecta bases existentes sin historial Alembic y aplica un `stamp` automático sobre la migración base `0001_initial_schema` antes de ejecutar `upgrade head`.

## 3. Crear nuevas migraciones

Cuando agregues o modifiques tablas, genera una nueva revisión:

```bash
make revision message="add provider weights"
```

El nuevo archivo aparecerá en `src/cambio_dollar/migrations/versions/`. Revisa y edita el contenido antes de enviar el cambio.

> Tip: Si prefieres usar autogeneración (basada en metadatos de SQLAlchemy), añade la bandera `--autogenerate`:
>
> ```bash
> python -m cambio_dollar.db_migrations revision "sync feature store" --autogenerate
> ```
>
> Asegúrate de revisar el resultado cuidadosamente; SQLite tiene limitaciones con `ALTER TABLE` y puede requerir migraciones manuales.

## 4. Flujo de trabajo recomendado

1. Ejecuta `make migrate` al comenzar el día o después de actualizar tu rama.
2. Aplica tus cambios de esquema (modelos, repositorio, etc.).
3. Genera una nueva migración con `make revision message="..."`.
4. Corre la suite de pruebas (`make test`) para validar que las migraciones y el código conviven correctamente.
5. Actualiza la documentación si el flujo implica pasos adicionales (por ejemplo, nuevos datos semilla).

## 5. Limpieza y resets

- Para reinicializar la base local desde cero:

  ```bash
  rm data/cambio_dollar.sqlite
  make migrate
  ```

- Si necesitas comenzar desde una instantánea previa, realiza un respaldo antes de ejecutar migraciones:

  ```bash
  cp data/cambio_dollar.sqlite data/backups/cambio_$(date +%Y%m%d%H%M).sqlite
  make migrate
  ```

## 6. Integración continua

La acción de CI (`.github/workflows/ci.yml`) debe ejecutar `make migrate` antes de `pytest` para garantizar que la base de datos efímera refleje el esquema actual. Si introduces nuevas migraciones, verifica que se ejecuten correctamente en entornos limpios.

## 7. Recursos adicionales

- Estrategia completa de migraciones: `docs/persistence_migration_strategy.md`.
- Documentación oficial de Alembic: <https://alembic.sqlalchemy.org/>.

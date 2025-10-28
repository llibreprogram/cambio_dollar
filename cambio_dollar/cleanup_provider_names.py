#!/usr/bin/env python3
"""
Script para limpiar nombres de proveedores con espacios extra en la base de datos.
Esto corrige el problema histórico de nombres con espacios al inicio/final.
"""

import sqlite3
from pathlib import Path


def cleanup_provider_names(db_path: Path) -> None:
    """Limpia espacios extra en los nombres de proveedores en la BD."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tablas que contienen nombres de proveedores
    tables_with_providers = [
        ('rate_snapshots', 'source'),
        ('provider_fetch_metrics', 'provider'),
        ('provider_reliability_metrics', 'provider'),
        ('provider_error_samples', 'provider'),
        ('anomaly_events', 'provider'),
    ]
    
    total_updated = 0
    
    for table_name, column_name in tables_with_providers:
        # Verificar si la tabla existe
        cursor.execute(f"""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='{table_name}'
        """)
        if not cursor.fetchone():
            print(f"⚠️  Tabla {table_name} no existe, omitiendo...")
            continue
        
        # Actualizar nombres con espacios
        cursor.execute(f"""
            UPDATE {table_name}
            SET {column_name} = TRIM({column_name})
            WHERE {column_name} != TRIM({column_name})
        """)
        updated = cursor.rowcount
        total_updated += updated
        
        if updated > 0:
            print(f"✅ {table_name}.{column_name}: {updated} registros actualizados")
        else:
            print(f"✓  {table_name}.{column_name}: Sin cambios necesarios")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"Total de registros actualizados: {total_updated}")
    print(f"{'='*70}")
    
    if total_updated > 0:
        print("\n✅ Limpieza completada exitosamente!")
        print("   Los nombres de proveedores ahora están normalizados.")
    else:
        print("\n✓  No se encontraron nombres con espacios extra.")


if __name__ == "__main__":
    # Ruta por defecto de la base de datos
    default_db = Path("data/cambio_dollar.sqlite")
    
    if not default_db.exists():
        print(f"❌ Error: No se encontró la base de datos en {default_db}")
        print("   Asegúrate de estar en el directorio raíz del proyecto.")
        exit(1)
    
    print("═" * 70)
    print("   LIMPIEZA DE NOMBRES DE PROVEEDORES")
    print("═" * 70)
    print(f"\nBase de datos: {default_db}")
    print("\nEste script eliminará espacios extra al inicio/final de los")
    print("nombres de proveedores en todas las tablas relevantes.\n")
    
    response = input("¿Continuar? (s/n): ").lower().strip()
    
    if response == 's' or response == 'si' or response == 'sí' or response == 'yes' or response == 'y':
        print("\nProcesando...\n")
        cleanup_provider_names(default_db)
    else:
        print("\n❌ Operación cancelada.")

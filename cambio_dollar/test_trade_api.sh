#!/bin/bash
# Script para probar el endpoint /api/trade

echo "═══════════════════════════════════════════════════════════════════════════"
echo "                   PRUEBA DEL ENDPOINT /api/trade"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# Verificar que el servidor está corriendo
if ! curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "❌ Error: El servidor no está corriendo en http://127.0.0.1:8000"
    echo "   Inicia el servidor con: make serve"
    exit 1
fi

echo "✅ Servidor activo"
echo ""

# Prueba 1: Registrar una venta
echo "📝 Prueba 1: Registrar venta de 100 USD a 63.5 DOP/USD"
echo "───────────────────────────────────────────────────────────────────────────"
RESPONSE=$(curl -X POST http://127.0.0.1:8000/api/trade \
  -H "Content-Type: application/json" \
  -d '{"action": "sell", "usd_amount": 100, "rate": 63.5, "fees": 25}' \
  -s -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "201" ]; then
    echo "✅ Operación registrada exitosamente (HTTP 201)"
    echo "$BODY" | python3 -m json.tool
else
    echo "❌ Error HTTP $HTTP_CODE"
    echo "$BODY"
fi

echo ""
echo "───────────────────────────────────────────────────────────────────────────"

# Prueba 2: Registrar una compra (sin tasa, usa consenso)
echo "📝 Prueba 2: Registrar compra de 50 USD (usando tasa de consenso)"
echo "───────────────────────────────────────────────────────────────────────────"
RESPONSE2=$(curl -X POST http://127.0.0.1:8000/api/trade \
  -H "Content-Type: application/json" \
  -d '{"action": "buy", "usd_amount": 50}' \
  -s -w "\n%{http_code}")

HTTP_CODE2=$(echo "$RESPONSE2" | tail -n1)
BODY2=$(echo "$RESPONSE2" | head -n-1)

if [ "$HTTP_CODE2" == "201" ]; then
    echo "✅ Operación registrada exitosamente (HTTP 201)"
    echo "$BODY2" | python3 -m json.tool
else
    echo "❌ Error HTTP $HTTP_CODE2"
    echo "$BODY2"
fi

echo ""
echo "───────────────────────────────────────────────────────────────────────────"

# Mostrar historial
echo "📊 Historial reciente de operaciones:"
echo "───────────────────────────────────────────────────────────────────────────"
curl -X POST http://127.0.0.1:8000/api/history \
  -s | python3 -m json.tool | head -50

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "                          PRUEBA COMPLETADA"
echo "═══════════════════════════════════════════════════════════════════════════"

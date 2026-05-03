# Integracion Bonita - Odoo para FCS

## Objetivo

Esta integracion conecta el workflow de Bonita con Odoo para FCS - Flores Cristo de la Sed.

La idea es mantener una separacion clara:

- Bonita gestiona el workflow del pedido: registro, comprobacion, preparacion, reparto, entrega e incidencias.
- Odoo gestiona los datos reales: pedidos FCS, productos, stock, listas de materiales, movimientos de stock, vehiculos y rutas.

Bonita no calcula stock ni rutas. Bonita llama a Odoo y guarda las respuestas relevantes en variables del caso.

La planificacion de rutas se hace por lote. Un caso individual de Bonita no debe lanzar la planificacion justo despues de preparar su pedido, porque eso planificaria demasiado pronto. Cada pedido preparado queda en Odoo en estado `prepared`. Despues, un disparador separado (operario, tarea programada o proceso batch de Bonita) llama una sola vez a `/fcs_route/plan_routes` con `batch=true` y Odoo decide las rutas con todos los pedidos preparados pendientes.

## Punto de entrada

Odoo se publica en:

```text
http://localhost:8069
```

Desde Bonita Runtime dentro de Docker, el host correcto suele ser:

```text
http://odoo:8069
```

Si se prueban los endpoints desde el equipo local con curl o Postman:

```text
http://localhost:8069
```

Si Odoo no selecciona automaticamente la base de datos, anadir `?db=system` a la URL.

## Token de practica

Todos los endpoints esperan:

```json
{
  "api_token": "fcs-demo-token"
}
```

Esto es una proteccion simple para la practica. En produccion deberia sustituirse por autenticacion segura, usuario tecnico o API keys bien gestionadas.

## Comprobacion automatica de stock

La logica reutilizable esta en el modulo `control_stock`, modelo abstracto:

```text
control.stock.service
```

El servicio recibe lineas con producto y cantidad. Para cada producto:

1. Busca una lista de materiales de tipo `phantom`.
2. Si existe BOM, calcula los componentes necesarios.
3. Si no existe BOM, comprueba el stock del producto directamente.
4. Consulta `product.free_qty`.
5. Devuelve si hay stock y una lista de faltantes.

Formato de respuesta:

```json
{
  "stock_ok": false,
  "missing_items": [
    {
      "product_id": 4,
      "product": "Rosa blanca",
      "required_qty": 40.0,
      "available_qty": 18.0,
      "missing_qty": 22.0,
      "uom": "Units"
    }
  ]
}
```

El modulo `fcs_route_planner` tiene un adaptador FCS:

```text
fcs.stock.integration.service
```

Ese adaptador convierte lineas FCS (`flower_type`, `product_id`, `product_name`, `quantity`) en lineas reales de producto para `control.stock.service`.

## Entrada y salida de mercancia

Entradas:

- Se recomienda usar el flujo estandar de Inventario de Odoo.
- Para una entrada real, crear una recepcion o ajuste de inventario del producto/material.
- No se escribe directamente en `stock.quant` desde la integracion.

Salidas:

- Al confirmar preparacion desde Bonita, Odoo comprueba stock de nuevo.
- Si hay stock y el pedido no habia consumido stock antes, se crean movimientos `stock.move` desde la ubicacion interna de stock hasta la ubicacion de cliente.
- Si el arreglo tiene BOM `phantom`, se consumen los componentes.
- Si no tiene BOM, se consume el propio producto.
- El pedido guarda `stock_consumed = True` y los `stock_move_ids` para evitar consumos duplicados.

## Endpoints

### 1. Crear pedido

```text
POST /fcs_route/create_order
```

Ejemplo:

```json
{
  "api_token": "fcs-demo-token",
  "name": "BONITA-001",
  "customer_name": "Familia Perez",
  "delivery_type": "funeral_home",
  "zone_name": "Nervion",
  "funeral_home_name": "Tanatorio SE-30",
  "order_time": "2026-05-03T10:00:00",
  "lines": [
    {
      "product_name": "Corona modelo 04",
      "flower_type": "corona",
      "quantity": 1
    }
  ],
  "notes": "Pedido creado desde Bonita"
}
```

Respuesta:

```json
{
  "success": true,
  "order_id": 12,
  "order_name": "BONITA-001",
  "state": "pending",
  "stock_ok": true,
  "missing_items": []
}
```

### 2. Comprobar stock

```text
POST /fcs_route/check_stock
```

Por pedido:

```json
{
  "api_token": "fcs-demo-token",
  "order_id": 12
}
```

Por lineas sueltas:

```json
{
  "api_token": "fcs-demo-token",
  "lines": [
    {
      "product_name": "Corona modelo 04",
      "quantity": 2
    }
  ]
}
```

### 3. Confirmar preparacion

```text
POST /fcs_route/confirm_preparation
```

```json
{
  "api_token": "fcs-demo-token",
  "order_id": 12
}
```

Si hay stock, consume materiales/productos y marca el pedido como `prepared`.

### 4. Consultar cola de reparto

```text
POST /fcs_route/route_queue
```

```json
{
  "api_token": "fcs-demo-token",
  "batch": true
}
```

Opcionalmente se puede exigir un minimo de pedidos antes de planificar:

```json
{
  "api_token": "fcs-demo-token",
  "batch": true,
  "minimum_orders": 5
}
```

Si hay menos pedidos preparados que `minimum_orders`, Odoo no planifica todavia y devuelve `planning_executed=false`.

Devuelve los pedidos `prepared` que aun no tienen ruta. Sirve para comprobar que los pedidos van acumulandose antes de lanzar la planificacion por lote.

### 5. Planificar rutas por lote

```text
POST /fcs_route/plan_routes
```

```json
{
  "api_token": "fcs-demo-token",
  "batch": true
}
```

Ejecuta el wizard existente con:

- `planning_datetime = now`
- `include_pending_only = true`
- `max_delivery_hours = 3`
- `allow_reasonable_detours = true`
- `max_reasonable_detour_minutes = 25`

El wizard planifica solo pedidos en estado `prepared` y sin ruta asignada. Por tanto, si entran 5 pedidos y los 5 llegan a preparados, una unica llamada a este endpoint decide las rutas para los 5 juntos.

### 6. Consultar estado

```text
POST /fcs_route/order_status
```

```json
{
  "api_token": "fcs-demo-token",
  "order_id": 12
}
```

### 7. Marcar entregado

```text
POST /fcs_route/mark_delivered
```

```json
{
  "api_token": "fcs-demo-token",
  "order_id": 12
}
```

## Pruebas con curl

Usar PowerShell en Windows. Cambiar `?db=system` si la base de datos tiene otro nombre.

Crear pedido:

```powershell
curl.exe -X POST "http://localhost:8069/fcs_route/create_order?db=system" -H "Content-Type: application/json" -d "{\"api_token\":\"fcs-demo-token\",\"name\":\"BONITA-001\",\"customer_name\":\"Familia Perez\",\"delivery_type\":\"funeral_home\",\"zone_name\":\"Nervion\",\"funeral_home_name\":\"Tanatorio SE-30\",\"order_time\":\"2026-05-03T10:00:00\",\"lines\":[{\"product_name\":\"Corona modelo 04\",\"flower_type\":\"corona\",\"quantity\":1}],\"notes\":\"Pedido creado desde Bonita\"}"
```

Crear pedido sin stock suficiente:

```powershell
curl.exe -X POST "http://localhost:8069/fcs_route/create_order?db=system" -H "Content-Type: application/json" -d "{\"api_token\":\"fcs-demo-token\",\"name\":\"BONITA-SIN-STOCK\",\"customer_name\":\"Prueba sin stock\",\"delivery_type\":\"funeral_home\",\"zone_name\":\"Nervion\",\"funeral_home_name\":\"Tanatorio SE-30\",\"order_time\":\"2026-05-03T10:00:00\",\"lines\":[{\"product_name\":\"Corona modelo 04\",\"flower_type\":\"corona\",\"quantity\":999}],\"notes\":\"Debe devolver faltantes\"}"
```

Comprobar stock de un pedido:

```powershell
curl.exe -X POST "http://localhost:8069/fcs_route/check_stock?db=system" -H "Content-Type: application/json" -d "{\"api_token\":\"fcs-demo-token\",\"order_id\":12}"
```

Confirmar preparacion:

```powershell
curl.exe -X POST "http://localhost:8069/fcs_route/confirm_preparation?db=system" -H "Content-Type: application/json" -d "{\"api_token\":\"fcs-demo-token\",\"order_id\":12}"
```

Planificar rutas:

```powershell
curl.exe -X POST "http://localhost:8069/fcs_route/plan_routes?db=system" -H "Content-Type: application/json" -d "{\"api_token\":\"fcs-demo-token\",\"batch\":true}"
```

Planificar rutas solo si hay al menos 5 pedidos preparados:

```powershell
curl.exe -X POST "http://localhost:8069/fcs_route/plan_routes?db=system" -H "Content-Type: application/json" -d "{\"api_token\":\"fcs-demo-token\",\"batch\":true,\"minimum_orders\":5}"
```

Consultar cola de pedidos preparados pendientes de ruta:

```powershell
curl.exe -X POST "http://localhost:8069/fcs_route/route_queue?db=system" -H "Content-Type: application/json" -d "{\"api_token\":\"fcs-demo-token\"}"
```

Consultar estado:

```powershell
curl.exe -X POST "http://localhost:8069/fcs_route/order_status?db=system" -H "Content-Type: application/json" -d "{\"api_token\":\"fcs-demo-token\",\"order_id\":12}"
```

Marcar entregado:

```powershell
curl.exe -X POST "http://localhost:8069/fcs_route/mark_delivered?db=system" -H "Content-Type: application/json" -d "{\"api_token\":\"fcs-demo-token\",\"order_id\":12}"
```

## Configuracion en Bonita Studio

Variables recomendadas:

- `odoo_order_id`: Integer
- `stock_ok`: Boolean
- `missing_items`: Text o JSON serializado
- `cliente`: Text
- `tipo_entrega`: Text
- `zona`: Text
- `direccion`: Text
- `tanatorio`: Text
- `ruta_asignada`: Text
- `vehiculo_asignado`: Text
- `pedido_entregado`: Boolean

Flujo recomendado:

1. `Registrar Pedido`
2. Conector REST a `/fcs_route/create_order`
3. Guardar `order_id` en `odoo_order_id`
4. Guardar `stock_ok`
5. Guardar `missing_items`
6. Tarea automatica `Comprobar stock` con conector REST a `/fcs_route/check_stock`
7. Compuerta XOR:
   - `stock_ok == true`: continua a `Preparar Arreglo`
   - `stock_ok == false`: va a `Gestionar incidencia`
8. Tras `Preparar Arreglo`, conector REST a `/fcs_route/confirm_preparation`
9. El caso queda preparado en Odoo y pendiente de ruta.
10. La planificacion de rutas se ejecuta fuera del caso individual, con un disparador batch que llama a `/fcs_route/plan_routes`.
11. Cuando el pedido tenga ruta asignada, la tarea `Confirmar entrega` llama a `/fcs_route/mark_delivered`.
12. Fin

Patron recomendado de Bonita:

- Proceso 1: `Gestion de pedidos`, un caso por pedido. Crea pedido, comprueba stock, gestiona incidencia, confirma preparacion y deja el pedido en cola de reparto.
- Proceso 2: `Planificacion de repartos`, manual o programado. Consulta `/fcs_route/route_queue` y llama `/fcs_route/plan_routes` con `batch=true` una vez para todos los pedidos preparados.

Desde Bonita Runtime Docker, usar:

```text
http://odoo:8069/fcs_route/check_stock?db=system
```

Desde el servidor local de Bonita Studio, usar:

```text
http://localhost:8069/fcs_route/check_stock?db=system
```

Cada conector REST debe enviar:

- Metodo: POST
- Header: `Content-Type: application/json`
- Body: JSON con `api_token`

## Limitaciones actuales

- La asociacion `flower_type -> product.product` se resuelve por `product_id`, `product_name` o, como ultimo recurso, buscando productos por nombre parecido al tipo de arreglo.
- Para una integracion mas robusta conviene rellenar `product_id` en cada linea FCS.
- La autenticacion es un token fijo de practica.
- No se integra Google Maps ni OR-Tools.
- La planificacion mantiene el algoritmo actual del wizard.

## Mejoras futuras

- Crear una tabla explicita de equivalencias entre `flower_type` y productos Odoo.
- Anadir API key segura por usuario tecnico.
- Exponer seleccion de productos en los formularios de Bonita.
- Registrar incidencias en Odoo con un estado o modelo especifico.
- Conectar entregas con rutas reales y tiempos reales.

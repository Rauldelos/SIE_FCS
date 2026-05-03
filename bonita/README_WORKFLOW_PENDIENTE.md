# Workflow Bonita FCS

Archivo de trabajo:

```text
bonita/exports/fcs_20260502_2046.bos
```

Este `.bos` ya ha sido adaptado para reflejar la integracion Bonita -> Odoo. Se conserva una copia del export original en:

```text
bonita/exports/fcs_20260502_2046.before-codex-workflow.bos
```

## Regla importante de rutas

La asignacion de rutas no debe ejecutarse una vez por cada pedido.

Si entran 5 pedidos, el comportamiento correcto es:

1. Cada caso de pedido se registra.
2. Cada caso crea o actualiza su pedido en Odoo.
3. Cada caso comprueba stock en Odoo.
4. Cada caso confirma preparacion en Odoo.
5. Odoo deja cada pedido en estado `prepared`.
6. Los pedidos preparados quedan acumulados en la cola de reparto.
7. Un flujo batch separado llama una sola vez a `/fcs_route/plan_routes` con `batch=true`.
8. Odoo calcula rutas con todos los pedidos preparados pendientes.

Por tanto, el caso individual de Bonita no llama a `/fcs_route/plan_routes` justo despues de preparar un pedido.

## Cambios reflejados en el .bos

El proceso principal queda asi:

```text
Registrar Pedido
-> Odoo create_order
-> Odoo check_stock
-> Confirmacion Pedido
   -> stockOk == true:
      Preparar Arreglo
      -> Odoo confirm_preparation
      -> Esperar ruta asignada
      -> Confirmar entrega
      -> Odoo mark_delivered
      -> Fin pedido
   -> stockOk == false:
      Gestionar incidencia
      -> Fin pedido
```

Tambien se ha incorporado un flujo separado de planificacion por lote:

```text
Inicio planificacion por lote
-> Odoo route_queue
-> Odoo plan_routes batch
-> Fin planificacion
```

Cambios concretos del diagrama:

- `Inicio1` pasa a `Registrar Pedido`.
- Se anade la tarea de servicio `Odoo create_order`.
- `Comprobar stock` pasa a tarea de servicio `Odoo check_stock`.
- La compuerta mantiene `stockOk == true` y `stockOk == false`; la rama sin stock queda como salida por defecto.
- Se anade `Gestionar incidencia` para la rama sin stock.
- `Preparar Arreglo` se mantiene como tarea humana.
- Se anade `Odoo confirm_preparation` tras preparar el arreglo.
- `Asignar Reparto` pasa a `Esperar ruta asignada`; sirve como espera humana/informativa, no como planificador automatico por pedido.
- `Confirmar entrega` se mantiene como tarea humana.
- Se anade `Odoo mark_delivered` antes del fin del pedido.
- Se anade un flujo batch con `Odoo route_queue` y `Odoo plan_routes batch`.

Variables presentes o esperadas en el proceso:

- `pedidos`
- `stockOk`
- `odooOrderId`
- `missingItems`
- `pedidoEntregado`
- `rutaAsignada`
- `vehiculoAsignado`

## Pendiente dentro de Bonita Studio

El `.bos` contiene las tareas de servicio y las descripciones de los endpoints, pero los conectores REST no se han fabricado a mano dentro del XMI. Es mejor configurarlos en Bonita Studio para que Bonita genere su propia estructura interna de conectores sin riesgo de corrupcion.

Pendiente al abrirlo en Studio:

- Configurar el conector REST de `Odoo create_order`.
- Configurar el conector REST de `Odoo check_stock`.
- Configurar el conector REST de `Odoo confirm_preparation`.
- Configurar el conector REST de `Odoo mark_delivered`.
- Configurar el conector REST de `Odoo route_queue`.
- Configurar el conector REST de `Odoo plan_routes batch`.
- Mapear respuestas JSON a variables del proceso.
- Revisar formularios: instanciacion, `Preparar Arreglo`, `Confirmar entrega` y `Gestionar incidencia`.

## URLs de Odoo

Desde Bonita Runtime dentro de Docker:

```text
http://odoo:8069
```

Desde Bonita Studio en el equipo local:

```text
http://localhost:8069
```

Si Odoo no selecciona la base de datos automaticamente, anadir:

```text
?db=system
```

Token de practica:

```json
{
  "api_token": "fcs-demo-token"
}
```

## Conectores REST a configurar

### Odoo create_order

Metodo:

```text
POST
```

URL local:

```text
http://localhost:8069/fcs_route/create_order?db=system
```

URL Docker:

```text
http://odoo:8069/fcs_route/create_order?db=system
```

Body orientativo:

```json
{
  "api_token": "fcs-demo-token",
  "name": "${referencia}",
  "customer_name": "${cliente}",
  "delivery_type": "${tipo_entrega}",
  "zone_name": "${zona}",
  "funeral_home_name": "${tanatorio}",
  "home_address": "${direccion}",
  "lines": [
    {
      "product_name": "${producto}",
      "quantity": ${cantidad}
    }
  ],
  "notes": "${notas}"
}
```

Guardar respuesta:

- `odooOrderId = response.order_id`
- `stockOk = response.stock_ok`
- `missingItems = response.missing_items` serializado como texto/JSON

### Odoo check_stock

```text
POST http://localhost:8069/fcs_route/check_stock?db=system
```

```json
{
  "api_token": "fcs-demo-token",
  "order_id": ${odooOrderId}
}
```

Guardar:

- `stockOk = response.stock_ok`
- `missingItems = response.missing_items`

### Compuerta Confirmacion Pedido

Rama con stock:

```groovy
stockOk == true
```

Rama sin stock:

```groovy
stockOk == false
```

La rama sin stock debe quedar marcada como flujo por defecto.

### Odoo confirm_preparation

```text
POST http://localhost:8069/fcs_route/confirm_preparation?db=system
```

```json
{
  "api_token": "fcs-demo-token",
  "order_id": ${odooOrderId}
}
```

Si `success=true`, Odoo deja el pedido en `prepared` y consume stock una sola vez.

Si `success=false`, no debe avanzar a reparto; usar `missingItems` para incidencia.

### Odoo route_queue

```text
POST http://localhost:8069/fcs_route/route_queue?db=system
```

```json
{
  "api_token": "fcs-demo-token"
}
```

Sirve para ver cuantos pedidos preparados estan esperando ruta.

### Odoo plan_routes batch

```text
POST http://localhost:8069/fcs_route/plan_routes?db=system
```

```json
{
  "api_token": "fcs-demo-token",
  "batch": true
}
```

Para esperar a tener al menos 5 pedidos:

```json
{
  "api_token": "fcs-demo-token",
  "batch": true,
  "minimum_orders": 5
}
```

### Odoo mark_delivered

```text
POST http://localhost:8069/fcs_route/mark_delivered?db=system
```

```json
{
  "api_token": "fcs-demo-token",
  "order_id": ${odooOrderId}
}
```

Guardar:

- `pedidoEntregado = true` si `success=true`

## Gestionar incidencia

La tarea `Gestionar incidencia` debe mostrar `missingItems` para que el usuario vea:

- producto/material faltante;
- cantidad necesaria;
- cantidad disponible;
- cantidad faltante.

Ejemplo de texto para el formulario:

```text
No hay stock suficiente. Revisar faltantes:
${missingItems}
```

## Validacion realizada

Se ha validado:

- El `.bos` final abre como ZIP.
- Mantiene `fcs/MANIFEST`.
- Mantiene el mismo numero de entradas que el original.
- El proceso `fcs/app/diagrams/Gestion de pedidos-1.0.proc` es XML/XMI valido.
- Las conexiones internas `source` y `target` apuntan a elementos existentes.
- El flujo principal y el flujo batch aparecen dentro del `.bos` final.

No se ha validado:

- Despliegue real en Bonita Studio, porque el entorno Bonita del proyecto no despliega correctamente en esta maquina.
- Ejecucion real de conectores REST dentro de Bonita, porque requieren configurar los conectores en Studio.

# Resúmenes de hallazgos por WhatsApp

## Objetivo

Permitir que un superusuario seleccione una empresa y un área, revise un resumen breve de los hallazgos vencidos y próximos a vencer, y lo envíe por WhatsApp al encargado de esa área.

La pantalla prepara una comunicación real basada en los datos actuales. No es un mensaje de prueba ni inicia envíos automáticos.

## Contexto existente

- `syh.Cliente` y `syh.Area` representan empresas y áreas, pero son modelos no administrados por Django. `Area` ya tiene responsable y email, pero no un teléfono de WhatsApp.
- `syh.Movimientos` referencia empresa y área, e incluye estado, hallazgo y fecha de cumplimiento.
- `utiles.notificaciones.WhatsAppClient` ya implementa la conexión autenticada con Vogel WhatsApp API y la validación/normalización del teléfono.
- El comando de recordatorio existente agrupa hallazgos por empresa y área. La nueva pantalla reutilizará el criterio de estado, pero aplicará la ventana solicitada de los próximos cinco días.

## Configuración de destinatarios

Crear un modelo administrado por Django para guardar un teléfono de WhatsApp por área. La configuración tendrá una clave de área única y el número internacional del encargado. La empresa asociada se obtiene desde `Area`; no se agregan columnas ni se modifican las tablas existentes de empresas y áreas.

La configuración se mantiene en Django y queda disponible solo para superusuarios. Es opcional: si el área no tiene un teléfono configurado, el modal abre con el destino vacío y el superusuario puede ingresarlo para ese envío, sin persistirlo.

## Flujo de envío

1. Un superusuario abre la herramienta de resúmenes de WhatsApp.
2. Selecciona una empresa y luego una de sus áreas. El servidor valida que el área pertenezca a la empresa seleccionada.
3. La aplicación consulta los hallazgos de esa empresa y área y prepara el mensaje.
4. Se abre un modal con el teléfono asociado al área precargado si existe; si no existe, el campo aparece vacío. En ambos casos el destino se puede editar para ese envío. El texto exacto que se enviará es de solo lectura y el teléfono ingresado no se persiste.
5. El superusuario confirma el envío. La interfaz realiza una solicitud `POST` protegida contra CSRF. Una solicitud `GET` nunca envía mensajes.
6. El servidor vuelve a validar permisos, empresa, área, teléfono y contenido, y envía mediante `WhatsAppClient`.
7. La interfaz informa si el gateway aceptó el mensaje o devuelve un error legible. La acción evita doble envío por clics repetidos mientras la solicitud está en curso.

La configuración del teléfono y la herramienta de envío quedan restringidas a superusuarios tanto en la interfaz como en las vistas del servidor.

## Criterio de hallazgos

Incluir movimientos del área seleccionada cuyo estado sea `Gestión en Curso` o `Incumplido` y cuya fecha de cumplimiento esté informada. Separar en dos grupos:

- **Vencidos:** fecha de cumplimiento anterior al día actual.
- **Por vencer:** fecha de cumplimiento desde hoy hasta cinco días calendario después, inclusive.

Excluir los estados `Cumplido` y `Desafectado`. Si no hay hallazgos en ninguno de los grupos, no ofrecer el envío y mostrar que no hay novedades para esa empresa y área.

## Contenido del mensaje

El texto será breve e incluirá el nombre de la empresa, el área, los totales de vencidos y por vencer, y hasta tres ejemplos en total. Cada ejemplo incluirá una descripción recortada y la fecha de cumplimiento. Si existen más registros, el texto indicará cuántos quedan fuera del resumen.

El modal muestra el mensaje final en un campo de solo lectura; el número de destino sí es editable. La edición del texto del mensaje queda fuera de alcance.

## Errores y datos sensibles

- Un teléfono vacío o inválido impide enviar. La falta de un teléfono guardado no impide abrir el modal: el superusuario puede ingresar un número para ese envío.
- Los errores de conexión o rechazo del gateway se muestran en la interfaz sin mostrar la API key.
- La clave sigue en el `.env` del servidor y nunca llega al navegador.
- El número editado en el modal no se persiste ni se escribe en logs.
- Un resultado exitoso significa que el gateway aceptó el mensaje; no confirma que el destinatario lo haya leído.

## Fuera de alcance

- Envío automático o programado de recordatorios.
- Alertas de salud del servidor, backups o workers.
- Modificación de las tablas preexistentes de empresas y áreas.
- Envío de email desde esta herramienta.
- Edición libre del texto en el modal.

## Criterios de aceptación

1. Solo un superusuario puede administrar los teléfonos por área y acceder a la herramienta.
2. Las áreas ofrecidas corresponden únicamente a la empresa seleccionada.
3. El resumen incluye los movimientos, estados y fechas definidos en este documento.
4. El modal muestra el destino guardado, o un campo vacío si no hay configuración, y el mensaje calculado antes de cualquier envío.
5. Cambiar el teléfono en el modal no altera el contacto persistido.
6. El mensaje solo se envía tras una acción `POST` confirmada por un superusuario.
7. El mensaje se envía al número editado para esa solicitud y se informa el resultado del gateway.
8. Si no hay teléfono válido o no hay hallazgos aplicables, no se envía; el teléfono no necesita estar guardado previamente.
9. La API key no se expone en respuestas, la interfaz ni registros.

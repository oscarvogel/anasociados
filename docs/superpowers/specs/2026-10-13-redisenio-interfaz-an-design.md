# Rediseño visual del portal AN

## Objetivo

Unificar la experiencia visual de las pantallas operativas de AN & Asociados y del portal público de hallazgos. El resultado debe sentirse como un solo producto, ser legible en escritorio y celular, y seguir permitiendo los mismos trabajos y respetando los permisos actuales.

El rediseño se basa en la identidad del sitio público de AN & Asociados, no en los colores por defecto del tema Datta Able que hoy domina el portal.

## Hallazgos del relevamiento

- El proyecto usa Django Templates con un layout autenticado compartido en `templates/layouts/base.html` y parciales de cabecera, navegación, sidebar, breadcrumb y scripts.
- Hay 35 plantillas en `templates/pages`; 32 heredan del layout común. Los módulos operativos incluyen móviles/viajes, Seguridad e Higiene (SYH), usuarios e informes/herramientas.
- La presentación actual combina Datta Able, Bootstrap, `static/src/css/an-custom.css` (380 líneas), estilos embebidos en páginas y 157 atributos HTML `style` en plantillas de página (incluidas las dos plantillas de correo); la página pública de hallazgos también tiene estilos propios.
- `an-custom.css` ya define tokens y componentes `an-*`, pero también modifica selectores globales como `.card`, encabezados, alertas, paginación y barras de progreso. Las páginas de viajes duplican estilos de KPI y tarjetas con paletas distintas.
- El frontend usa interacciones existentes de Vue 2 y Vue 3, jQuery/AJAX, Chart.js, modales Bootstrap, tablas y descargas. El rediseño no requiere migrar estas tecnologías.
- El layout actual muestra controles de tema y navegación con contenido de muestra o destinos sin función. El rediseño no debe presentar controles ficticios como funciones disponibles.
- La página pública de detalle es independiente del shell autenticado. Debe conservar acceso por token, límites de datos, expiración y revocación existentes.
- El sitio público identifica el logo como `logo_almada_neri.png`. Su HTML utiliza principalmente `#3B5D30`, `#556B2F`, `#2C4A1D`, `#F2F6EC` y `#D4E7D3`.

## Alcance

### Incluido

- El shell autenticado: encabezado, navegación lateral, contenido, títulos de página y breadcrumb.
- La pantalla de inicio de sesión de `templates/admin/login.html`, con un rediseño completo y una identidad AN clara. Comparte los tokens institucionales, pero conserva un layout de acceso propio.
- Las páginas operativas activas: tablero, hallazgos, excesos, resumen mensual, móviles, personal, vencimientos, combustible, gastos, viajes y reportes; perfil y reporte de accesos; y envío del resumen por WhatsApp.
- La página pública de detalle de hallazgos, con el mismo lenguaje visual y logo, pero sin navegación o elementos que requieran autenticación.
- Componentes que se repiten: filtros, formularios, botones, tablas, tarjetas KPI, alertas, estados, modales, paginación, gráficos, estados vacíos y mensajes de carga/error.
- Adaptación responsive, accesibilidad visual y revisión de navegación para los permisos y roles que ya existen.

### Excluido

- Django Admin y sus plantillas personalizadas, excepto la pantalla de inicio de sesión indicada en el alcance. Las demás mantienen su flujo y apariencia durante esta iniciativa.
- Plantillas de correo `hallazgos_incumplidos.html` y `recordatorio_hallazgos.html`. Sus estilos en línea son parte de la compatibilidad con clientes de correo y no deben convertirse a CSS de navegador.
- Páginas de muestra del tema, componentes de demostración, gráficos/mapas de ejemplo y pantallas no enlazadas desde los flujos activos. Antes de excluir una plantilla se confirmará que no la usa una ruta operativa.
- Cambios de lógica de negocio, API, permisos, modelos, filtros, nombres de URL, reglas de acceso o contratos de datos.
- Migración a SPA, incorporación de un framework JavaScript/CSS o actualización general de dependencias.
- Rediseño del sitio institucional público; se toma como referencia de marca, no se modifica.

## Dirección visual

### Identidad

- Usar el logo institucional `logo_almada_neri.png` del sitio de AN. Si el asset todavía no está disponible en el repo, incluir una copia local apropiada para el portal. Mantener proporción y espacio de seguridad; no recrear ni recolorear el logo.
- Adoptar una paleta basada en la identidad institucional: verde `#3B5D30` para acciones y acentos principales, verde oscuro `#2C4A1D` para énfasis, oliva `#556B2F` como acento secundario, y `#F2F6EC` / `#D4E7D3` para fondos suaves.
- Definir neutrales para texto, bordes y superficies. Los colores de éxito, advertencia, error e información deben conservar significados distintos y cumplir contraste suficiente; no se reemplazan automáticamente por verdes institucionales.
- Definir una escala de tipografía, espacios, radios, sombras, foco y capas a través de tokens CSS reutilizables. Evitar gradientes y colores de acento distintos por página salvo que representen un dato semántico.

### Interfaz

- Crear una jerarquía clara de página: encabezado con título y contexto, acciones principales visibles, filtros agrupados, contenido y estados.
- Simplificar el shell: marca y navegación consistentes, menú comprensible en móvil y escritorio, estado activo visible, y solo controles que tengan una acción real.
- Rediseñar el login como puerta de entrada institucional: logo oficial, paleta AN, formulario enfocado, textos en español, errores claros y adaptación móvil. No incluir menú del portal ni controles decorativos que distraigan del acceso.
- Usar estilos compartidos para botones, campos, tablas, tarjetas, badges, alertas y modales. Mantener textos y acciones existentes salvo contenido de muestra que hoy se presenta como control funcional.
- Hacer tablas legibles en pantallas chicas mediante scroll contenido o presentación adaptable, sin ocultar columnas/datos esenciales ni cambiar filtros o paginación.
- En la página pública, conservar el carácter de lectura y el flujo actual del token. El diseño debe destacar empresa, área, cantidades y grupos de vencidos/próximos a vencer, con vencimiento del enlace claro y diseño apto para celular.
- Añadir estados visibles y consistentes para carga, ausencia de resultados, errores y confirmaciones. Mantener accesibilidad por teclado, foco visible, contraste y respeto a `prefers-reduced-motion`.

## Arquitectura de estilos

- Mantener Django Templates y Bootstrap como soporte de grilla/utilidades mientras se migran las páginas.
- Definir una única fuente de verdad para tokens y componentes AN bajo `static/src/css/`; separar los estilos del shell, componentes y páginas únicamente si el tamaño lo justifica.
- Mantener clases propias con prefijo `an-` y evitar reglas globales que redefinan `.card`, `h1`–`h6`, `.alert-*`, `.progress-bar`, `.pagination` u otros componentes Bootstrap sin un alcance explícito.
- Migrar estilos de páginas activas desde bloques `<style>` y atributos `style` a clases compartidas o clases locales acotadas. Los valores dinámicos imprescindibles (por ejemplo, progreso generado en tiempo de ejecución) pueden seguir asignándose desde JavaScript.
- Mantener los nombres de clases/hook que consume JavaScript, Vue, jQuery, gráficos o Bootstrap. Si un hook visual y un hook de comportamiento están acoplados, separarlos con atributos `data-*` solo cuando sea seguro y dentro de la pantalla que se migra.
- El portal público puede conservar un layout propio, pero consumirá los mismos tokens institucionales mediante CSS estático común; no debe duplicar la paleta.
- No retirar los assets de Datta Able/Bootstrap hasta comprobar que ninguna página incluida depende de ellos. El plan los reducirá de forma gradual y segura.

## Restricciones de comportamiento

- No cambiar endpoints, métodos HTTP, parámetros, serialización, permisos, control CSRF, datos visibles, fórmulas de indicadores, reglas de negocio ni persistencia.
- No migrar Vue 2 a Vue 3 ni Chart.js entre versiones como parte del rediseño.
- Preservar filtros, tablas, exportaciones, descargas, impresión, formularios, confirmaciones, modales y enlaces existentes.
- El acceso público al detalle mantiene token aleatorio, alcance por empresa/área, expiración de 14 días, revocación, almacenamiento de hash y respuestas no cacheadas/no indexables.
- El inicio de sesión conserva la vista/formulario Django actual, validación, protección CSRF, errores, redirecciones y política de autenticación; el cambio es visual y de textos visibles.
- La separación entre páginas operativas, Django Admin y correos debe mantenerse; los nuevos estilos no pueden cambiar inadvertidamente estos contextos.

## Enfoques considerados

1. **Consolidar el sistema actual por etapas (elegido).** Mantiene Django Templates, Bootstrap y el JavaScript existente; define componentes/tokens comunes y migra el shell y las páginas activas. Menor riesgo operativo y permite entregar valor módulo a módulo.
2. **Reemplazar todo el frontend por una SPA.** Da control visual completo, pero implica migrar rutas, autenticación, API y pantallas que hoy funcionan. No se justifica para resolver inconsistencias visuales.
3. **Agregar otra capa de overrides CSS.** Es rápido al principio, pero perpetúa la cascada y las diferencias actuales. No se recomienda.

## Implementación por etapas

1. **Inventario y línea base:** confirmar rutas/templates realmente activos, clasificar estilos compartidos y locales, registrar interacciones existentes y verificar disponibilidad/calidad de logo y favicon institucionales.
2. **Fundación visual:** definir tokens de marca y semánticos, tipografía, espaciado, foco, superficies y componentes base. Evitar cambios globales accidentales a Bootstrap/Admin/correos.
3. **Login:** rediseñar `templates/admin/login.html` y su layout de autenticación para que la primera pantalla ya presente la identidad AN; conservar intacto el flujo de autenticación.
4. **Shell compartido:** actualizar marca, header, sidebar, navegación móvil, breadcrumb y contenedor de página; retirar controles de muestra sin acción real.
5. **Pantallas piloto:** migrar Hallazgos y una pantalla frecuente de Móviles/Viajes para ajustar filtros, formularios, tablas, tarjetas KPI, estados y modales sobre casos reales.
6. **Migración de módulos:** aplicar componentes aprobados a SYH, Móviles/Informes, Usuarios y WhatsApp, una pantalla o conjunto de pantallas acopladas por vez; luego unificar la página pública con los tokens.
7. **Limpieza y cierre:** quitar estilos duplicados de las pantallas migradas, revisar selectores CSS restantes, verificar que el resto de Admin/correos/demos no haya cambiado y documentar el sistema visual resultante.

El orden exacto de pantallas se cierra en el plan de implementación, a partir de rutas activas y uso operativo. Cada etapa debe quedar desplegable sin esperar la reescritura del resto del sitio.

## Criterios de aceptación

- Las pantallas dentro del alcance comparten paleta, tipografía, espaciado, jerarquía de títulos, controles y estados visuales.
- El logo institucional se muestra sin deformación en escritorio y móvil; la marca coincide con el sitio institucional.
- La pantalla de login se identifica de forma inequívoca con AN & Asociados, es usable en celular y presenta errores de acceso con claridad.
- No quedan colores/gradientes decorativos incompatibles entre páginas activas; las diferencias de color restantes comunican estados o datos.
- Layout y tablas se pueden usar en anchos móviles y de escritorio; no hay controles cortados ni contenido operativo esencial inaccesible.
- Foco de teclado, contraste y movimiento reducido se contemplan en el sistema común.
- Las capacidades existentes, filtros, formularios, permisos, respuestas, gráficos, archivos, impresión y enlace público mantienen su comportamiento.
- El token público continúa sin figurar en la ruta HTTP, no habilita datos vencido/revocado y el documento conserva políticas de no cacheo/indexación.
- Django Admin, correos HTML y demos fuera de alcance conservan su comportamiento y no reciben estilos del nuevo sistema por selectores globales.

## Verificación prevista

- Revisión visual manual en anchos aproximados de 360–390 px, 768 px y 1366–1440 px, en las pantallas de cada etapa.
- Recorrido manual en staging para login/permisos y navegación, filtros, tablas/paginación, crear/editar/eliminar donde ya exista, modales, gráficos, descargas, impresión y enlace público.
- Verificar inicio de sesión correcto e incorrecto, CSRF, retorno al destino solicitado y estados de error sin alterar autenticación ni permisos.
- Revisión de contraste, navegación por teclado, foco visible, mensajes de carga/error/vacío y preferencia de movimiento reducido.
- Inspección de CSS para confirmar que las pantallas migradas ya no dependen de estilos duplicados y que los selectores globales no alteran Admin ni correos.
- Confirmar que no hubo cambios en rutas, contratos de API, consultas o reglas de negocio.

## Referencias de marca

- Sitio institucional: [anasociados.com.ar](https://anasociados.com.ar/).
- Logo referido por el sitio: `/assets/images/logo_almada_neri.png`.
- Colores observados en el HTML público: `#3B5D30`, `#556B2F`, `#2C4A1D`, `#F2F6EC`, `#D4E7D3`.
- Punto de partida actual del portal Django: `static/src/css/an-custom.css`, que usa azul `#04a9f5` y selectores globales sobre el tema Datta Able.

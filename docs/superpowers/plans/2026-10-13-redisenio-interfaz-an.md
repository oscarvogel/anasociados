# Rediseño visual del portal AN — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unificar las pantallas internas, el login y el portal público de hallazgos con la marca AN, manteniendo los flujos y contratos existentes.

**Architecture:** Refactorizar el CSS AN actual como sistema de tokens y componentes con estilos delimitados por contexto (`an-app`, `an-auth`, `an-public`). Mantener Django Templates, Bootstrap y el JavaScript actual; migrar la pantalla de login, el shell y los módulos por etapas.

**Tech Stack:** Django Templates, CSS, Bootstrap existente, Vue 2/Vue 3, jQuery y Chart.js existentes; sin nuevas dependencias.

**Spec:** `docs/superpowers/specs/2026-10-13-redisenio-interfaz-an-design.md`

## Global Constraints

- Cambios exclusivamente visuales y de textos de interfaz aprobados; preservar permisos, CSRF, URLs, APIs, datos, fórmulas, filtros y persistencia.
- No migrar Django Templates, Bootstrap, Vue ni Chart.js a otros frameworks o versiones.
- La paleta institucional parte de `#3B5D30`, `#2C4A1D`, `#556B2F`, `#F2F6EC` y `#D4E7D3`; mantener neutrales y estados semánticos contrastantes.
- Las páginas operativas, login y página pública usan clases `an-*`; evitar overrides globales sobre Bootstrap.
- El login conserva el flujo de Django, sus nombres de campo, CSRF, errores y redirecciones.
- El detalle público conserva token en fragmento, autorización Bearer, alcance, expiración, revocación y políticas anti-cache/anti-indexación.
- El CRUD activo de Django Admin también integra el rediseño porque es una pantalla operativa; correos y demos del tema quedan fuera.
- Verificar cada etapa de forma visual/manual en escritorio y móvil; no agregar bibliotecas frontend.

## Review Focus

- **Login fallido o retorno a `next`:** verificar que los errores sean claros y el destino/flujo de Django no cambie en Task 2.
- **CRUD Admin pierde hooks:** preservar los bloques y clases que Django usa para formularios, filtros, acciones, validaciones y tablas.
- **Estilos alcanzan correos:** revisar el alcance de selectores en Tasks 1 y 8; correo y demos deben conservarse.
- **IDs/clases consumidos por Vue, AJAX o gráficos:** comparar hooks antes/después y recorrer acciones en las Tasks 4–6.
- **Overflow en tablas, filtros y navegación móvil:** revisar a 360–390 px y 768 px en Tasks 3–7.
- **Acceso público o token cambia visualmente y deja de funcionar:** abrir página con/sin token y confirmar respuesta válida/no válida en Task 7.

---

### Task 1: Marca institucional y base del sistema visual

**Files:**
- Create: `static/assets/images/logo_almada_neri.png` (asset oficial del sitio institucional)
- Modify: `static/src/css/an-custom.css`
- Modify: `templates/includes/head.html`
- Modify: `templates/layouts/base.html`
- Modify: `templates/layouts/base-auth.html`
- Modify: `templates/pages/utiles/hallazgos_publicos.html`

**Interfaces:**
- Provides CSS tokens `--an-color-primary`, `--an-color-primary-strong`, `--an-color-accent`, `--an-color-surface`, `--an-color-surface-soft`, `--an-color-text`, `--an-color-muted`, `--an-color-border`, and semantic success/warning/danger/info tokens.
- Provides body scopes `.an-app`, `.an-auth`, and `.an-public` for shell-specific rules.

- [x] Add the official logo at `static/assets/images/logo_almada_neri.png`; confirm its intrinsic dimensions and preserve its aspect ratio.
- [x] Replace the current blue token values with the approved institutional palette; define readable neutral surfaces, text, borders, focus ring, and status colors.
- [x] Scope body, heading, card, alert, progress, pagination, and form rules under the appropriate `an-*` context; remove broad unscoped selectors.
- [x] Add `an-app`, `an-auth`, and `an-public` body classes in their layouts and public page; preserve the existing static asset loading order.
- [ ] Manually inspect representative app, auth, public, and CRUD Admin screens; verify that styles do not reach email templates or theme demos.

### Task 2: Rediseñar completamente el login

**Files:**
- Modify: `templates/layouts/base-auth.html`
- Modify: `templates/admin/login.html`
- Modify: `static/src/css/an-custom.css`

**Interfaces:**
- Consumes the `an-auth` scope and shared brand tokens from Task 1.
- Preserves Django form fields `form.username` and `form.password`, POST method, CSRF token, `next` redirect behavior, and form errors.

- [x] Build a focused, responsive access screen with the official logo, AN colors, Spanish title/labels, one username field, one password field, and a prominent “Iniciar sesión” action.
- [x] Remove theme/demo decoration and the hidden theme switch; do not add links or controls for features that do not exist.
- [x] Keep field `name`/`id`, POST target, CSRF handling, form error values, and authenticated-user warning behavior intact.
- [ ] Manually check the screen at mobile and desktop widths, valid/invalid credentials, keyboard focus, and a login request carrying a `next` destination.

### Task 3: Unificar shell autenticado y navegación

**Files:**
- Modify: `templates/layouts/base.html`
- Modify: `templates/includes/navigation.html`
- Modify: `templates/includes/sidebar.html`
- Modify: `templates/includes/breadcrumb.html`
- Modify: `templates/includes/head.html`
- Modify: `static/src/css/an-custom.css`

**Interfaces:**
- Consumes shared tokens/components from Task 1.
- Preserves every existing route tag and role/superuser conditional for active links.

- [x] Apply the official logo, palette, typography, content spacing, and page heading hierarchy to the authenticated shell.
- [x] Rework sidebar grouping, active state, collapse behavior, and mobile navigation without changing link targets or permission guards.
- [x] Remove nonfunctional demo search, notifications, theme control, and placeholder links from the header; keep real profile/logout/password actions.
- [x] Translate visible shell labels to Spanish and set document language to `es` in the applicable layouts.
- [ ] Manually traverse each role’s navigation at desktop/mobile widths and confirm every prior live route remains reachable.

### Task 3b: Integrar el CRUD activo de Django Admin

**Files:**
- Modify: `templates/admin/change_list.html`
- Modify: `templates/admin/change_form.html`
- Modify: `templates/admin/syh/excesosvelocidad/change_form.html`
- Modify: `templates/admin/delete_confirmation.html`
- Modify: `templates/admin/delete_selected_confirmation.html`
- Modify: `templates/admin/change_list_results.html`
- Modify: `templates/admin/actions.html`
- Modify: `templates/admin/filter.html`
- Modify: `templates/admin/submit_line.html`
- Modify: `static/src/css/an-custom.css`

**Interfaces:**
- The custom CRUD templates continue to extend the authenticated shell.
- Preserve Django Admin blocks, forms, field names, validation, permissions, actions, CSRF, pagination, search, filters, and model URLs.

- [x] Bring changelist tables, search, filters, object tools, pagination, change forms, inline formsets, and confirmation actions into the shared AN component language.
- [x] Preserve all admin template blocks and Django-generated IDs/classes consumed by its JavaScript.
- [ ] Manually inspect `/admin/syh/area/` and one representative model form at desktop/mobile widths, including validation and action controls.

### Task 4: Componentes compartidos y pantallas SYH

**Files:**
- Modify: `static/src/css/an-custom.css`
- Modify: `templates/pages/index.html`
- Modify: `templates/pages/syh/visualizar_movimientos.html`
- Modify: `templates/pages/syh/excesos_velocidad.html`
- Modify: `templates/pages/syh/resumen_mensual.html`
- Modify: `templates/pages/utiles/whatsapp_hallazgos.html`

**Interfaces:**
- Provides shared selectors `.an-page-header`, `.an-card`, `.an-filter-bar`, `.an-button`, `.an-field`, `.an-table-wrapper`, `.an-table`, `.an-badge`, `.an-alert`, `.an-modal`, and loading/empty/error states.
- Existing Vue selectors, element IDs, and `data-*` URLs stay unchanged.

- [x] Define reusable page header, card, form, button, table, badge, alert, modal, pagination, and state styles with scoped `an-*` classes.
- [x] Migrate dashboard, Hallazgos, Excesos, Resumen Mensual, and WhatsApp summary to the shared components while preserving selectors and chart containers used by JavaScript.
- [x] Replace static inline presentation values in these pages with shared classes; leave only runtime-generated visual values in JavaScript.
- [ ] Manually traverse filters, chart display, WhatsApp preview/send confirmation, table actions, and monthly report download at desktop/mobile sizes.

### Task 5: Migrar pantallas de gestión de Móviles

**Files:**
- Modify: `templates/pages/moviles/movil_list.html`
- Modify: `templates/pages/moviles/tipo_vencimientos_list.html`
- Modify: `templates/pages/moviles/vencimientos_list.html`
- Modify: `templates/pages/moviles/personal_list.html`
- Modify: `templates/pages/moviles/carga_combustible_list.html`
- Modify: `templates/pages/moviles/gastos_moviles_list.html`
- Modify: `templates/pages/moviles/matafuegos_list.html`
- Modify: `static/src/css/an-custom.css`

**Interfaces:**
- Uses Task 4 shared form, button, modal, alert, and table classes.
- Preserves API endpoints, Vue instance roots, event handlers, pagination hooks, and permission checks.

- [x] Apply consistent title/action/filter/table/modal patterns to each management page.
- [x] Remove locally duplicated inline styles and align status/action treatments without changing action availability.
- [x] Keep selectors consumed by Vue 2, Axios, pagination components, and existing APIs unchanged.
- [ ] Manually check list, search/filter, create/edit/delete flows and pagination where present, including mobile overflow.

### Task 6: Viajes, informes y usuarios

**Files:**
- Modify: `templates/pages/moviles/viajes_list.html`
- Modify: `templates/pages/moviles/viajes_graficos.html`
- Modify: `templates/pages/moviles/consumo_combustible_por_mes.html`
- Modify: `templates/pages/moviles/reporte_gastos_movil.html`
- Modify: `templates/pages/usuarios/update_user.html`
- Modify: `templates/pages/usuarios/reporte_accesos.html`
- Modify: `static/src/css/an-custom.css`

**Interfaces:**
- Uses Task 4 shared components; chart containers and existing Vue 3/Chart.js interfaces remain unchanged.

- [x] Replace duplicated KPI and trip-card palettes/styles with shared tokens and components; retain data-specific status colors only where they carry meaning.
- [x] Align report filters, charts, tables, date controls, and downloads with the common hierarchy.
- [x] Apply consistent form/profile and access-report styles while retaining existing fields, routes, filters, and access restrictions.
- [ ] Manually check trip filters/actions, charts, expense report date/company filters, exports/downloads, profile editing, and access report behavior.

### Task 7: Portal público de hallazgos

**Files:**
- Modify: `templates/pages/utiles/hallazgos_publicos.html`
- Modify: `static/src/css/an-custom.css`

**Interfaces:**
- Uses shared brand tokens from Task 1 under `.an-public`, without loading the authenticated shell.
- Retains the current heading brand text `AN & Asociados` and caption `Consultoría y Servicios`.

- [x] Replace the page’s duplicated brand color variables with shared institutional tokens while retaining its independent read-only layout.
- [x] Keep company/area counts, overdue/upcoming groups, complete finding descriptions, state, due date, and link expiry presentation clear on mobile and desktop.
- [x] Preserve token extraction from the URL fragment, Bearer fetch, noindex/no-store/referrer policy, and the current error/expired/revoked states.
- [ ] Manually open a valid link and invalid/expired/revoked links; confirm content and security behavior remain unchanged.

### Task 8: Limpieza y verificación final

**Files:**
- Modify: `static/src/css/an-custom.css`
- Review/clean remaining inline presentation in: `templates/pages/index.html`, `templates/pages/syh/resumen_mensual.html`, `templates/pages/moviles/movil_list.html`, `templates/pages/moviles/viajes_list.html`, `templates/pages/moviles/viajes_graficos.html`, `templates/pages/moviles/reporte_gastos_movil.html`, `templates/pages/utiles/hallazgos_publicos.html`
- Exclude: email templates and demo pages; keep unrelated Admin pages outside the active CRUD flow unchanged

- [x] Search in included templates for leftover inline presentation attributes, embedded style blocks, old palette literals, and page-specific duplicate KPI/card styles; migrate only styles covered by the spec.
- [x] Search shared CSS for selectors that could affect email templates or demos outside the authenticated shell.
- [ ] Manually review login and every included module at 360–390 px, 768 px, and 1366–1440 px; verify keyboard focus, contrast, reduced motion, loading/error/empty states, and table usability.
- [ ] Manually confirm routes, permissions, Admin CRUD submissions/actions, filters, charts, downloads, printing, WhatsApp sending, and public-token behavior have not changed.
- [ ] Review final diff and document any intentionally retained styles that belong to excluded pages or dynamic runtime values.

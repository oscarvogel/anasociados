# Resúmenes de hallazgos por WhatsApp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Follow the task boundaries and interfaces below.

**Goal:** Let superusers send a concise WhatsApp summary of overdue and near-due findings for one selected company and area.

**Architecture:** Add a Django-managed per-area contact record without changing the unmanaged company/area tables. A focused service builds the summary; superuser-only Django views provide company/area selection, a signed preview, and a confirmed send through the existing `WhatsAppClient`.

**Tech Stack:** Django 5.2, Python, existing `WhatsAppClient`/requests integration, existing Bootstrap-based templates, MySQL.

**Spec:** `docs/superpowers/specs/2026-10-13-resumenes-hallazgos-whatsapp-design.md`

## Global Constraints

- Only superusers may configure area phone numbers or use the sending interface.
- `Cliente` and `Area` remain unmanaged and unchanged.
- The phone shown in the modal is editable for one send only; do not persist the override.
- Include open `Gestión en Curso` and `Incumplido` movements with a due date before today or from today through five calendar days ahead, inclusive.
- The message includes company, area, category totals, and at most three shortened examples total.
- Sending requires a CSRF-protected `POST`; `GET` requests never send messages.
- Keep the API key on the server; never return it to the browser or log it.
- Do not send email, schedule automatic notifications, or alter server-health alerts in this feature.

## Review Focus

- Non-superuser direct access to the page or JSON endpoints: reject server-side (Task 3).
- An area ID that does not belong to the submitted company ID: reject before preview or send (Tasks 2–3).
- Missing or malformed destination phone: reject without sending. A valid one-send override is not persisted and does not require a saved area contact (Task 3).
- No matching records, null due dates, or records outside the five-day window: display no updates and do not send (Task 2).
- Gateway timeout, non-success status, or malformed response: return a safe error without exposing the API key (Task 3).

---

### Task 1: Persist and administer one WhatsApp contact per area

**Files:**
- Create: `utiles/models.py`
- Create: `utiles/admin.py`
- Create: `utiles/migrations/__init__.py`
- Create: `utiles/migrations/0001_initial.py` (generated from the model)

**Interfaces:**
- Produces `AreaWhatsAppContacto`, a Django-managed record uniquely associated with one `syh.Area` and containing the saved international phone number.
- Use a relation to `syh.Area` with `db_constraint=False`; `syh.Area` is unmanaged and must not gain a database constraint or schema change.
- Expose the record in Django admin for superusers only.

- [ ] Add `AreaWhatsAppContacto` with a unique one-to-one area relation (`db_constraint=False`), a phone field, and an `updated_at` timestamp.
- [ ] Register it in `utiles/admin.py`; expose the area and phone fields, and explicitly restrict admin view/add/change/delete operations to superusers.
- [ ] Generate and review the `utiles` initial migration; confirm it creates only the managed contact table and does not alter `syh_cliente` or `syh_area`.
- [ ] Run `python manage.py check` and `python manage.py migrate --plan`; confirm the new table is the only planned schema operation.
- [ ] Commit as `feat: agregar destinatario WhatsApp por area`.

### Task 2: Build the findings summary for a selected company and area

**Files:**
- Create: `utiles/alertas_hallazgos.py`
- Read: `syh/models.py` (`Cliente`, `Area`, and `Movimientos`)

**Interfaces:**
- Produces frozen dataclass `ResumenHallazgosWhatsApp` with string `cliente`, string `area`, `list[Movimientos]` fields `vencidos` and `por_vencer`, integer totals, string `mensaje`, and boolean `hay_novedades`.
- Produces `construir_resumen_hallazgos_whatsapp(cliente_id: str, area_id: str, hoy: date | None = None) -> ResumenHallazgosWhatsApp`.
- Raise `SeleccionEmpresaAreaInvalida` when the company or area is missing, or the area does not belong to the selected company.

- [ ] Query only the selected company and area; include states `Gestión en Curso` and `Incumplido` with a non-null `fecha_cumplimiento`.
- [ ] Use `timezone.localdate()` when `hoy` is omitted. Classify dates before today as overdue and dates today through `hoy + 5 days` inclusive as upcoming.
- [ ] Order each group by due date and movement ID for stable results; exclude `Cumplido`, `Desafectado`, null dates, and dates after the five-day window.
- [ ] Format the Spanish WhatsApp message with company/area, both totals, at most three example lines across both groups, descriptions capped at 100 characters, and a count of omitted records.
- [ ] Return `hay_novedades=False` and an empty or explanatory summary when both groups are empty; do not create a sendable summary in that case.
- [ ] Run `python manage.py check`; confirm the new service imports without introducing a model or settings cycle.
- [ ] Commit as `feat: preparar resumen WhatsApp de hallazgos`.

### Task 3: Add restricted preview and send endpoints

**Files:**
- Create: `utiles/views.py`
- Create: `utiles/urls.py`
- Modify: `core_an/urls.py`
- Modify: `utiles/notificaciones.py` only if a small reusable client-level adjustment is required

**Interfaces:**
- `whatsapp_hallazgos_page(request)`: superuser-only HTML page.
- `whatsapp_hallazgos_areas(request)`: superuser-only `GET`, returns areas for a company.
- `whatsapp_hallazgos_preview(request)`: superuser-only `GET`, returns the saved area phone or an empty destination when none is configured, plus the message preview and a signed preview token.
- `whatsapp_hallazgos_send(request)`: superuser-only CSRF-protected `POST`, accepts the signed preview token and edited phone, then sends the signed message via `WhatsAppClient.enviar_texto`.

- [ ] Add a shared superuser guard for every page and JSON endpoint; direct requests from non-superusers receive HTTP 403.
- [ ] In the area endpoint, verify the company exists and query only its areas.
- [ ] In preview and send, revalidate that the area belongs to the company; block when there are no matching findings. The per-area contact is optional and only supplies a default phone.
- [ ] Sign the selected company ID, area ID, exact generated message, and a unique preview nonce with Django signing and a five-minute maximum age. The send endpoint uses the signed message, not message text supplied by the browser, so the displayed message is the one sent.
- [ ] Validate and normalize the editable phone using `WhatsAppClient.normalizar_telefono`; never save the override or include it in logs.
- [ ] Call the existing `WhatsAppClient.enviar_texto` with an `external_ref` derived from the preview nonce (stable for retries of that preview, unique for a new preview); return only the gateway acceptance/message ID or a safe error.
- [ ] Ensure API errors and exceptions cannot expose `WHATSAPP_API_KEY`; reject send requests using `GET` or without a valid signed preview.
- [ ] Define `app_name = "utiles"`, include the URL module under `/utiles/`, and confirm the three route names reverse under the `utiles` namespace.
- [ ] Commit as `feat: agregar endpoints protegidos para alertas WhatsApp`.

### Task 4: Add the company/area selection and confirmation modal

**Files:**
- Create: `templates/pages/utiles/whatsapp_hallazgos.html`
- Modify: `templates/includes/sidebar.html`

**Interfaces:**
- The template consumes the page and JSON endpoints from Task 3.
- Page navigation is visible only to superusers; server authorization remains authoritative.

- [ ] Add company and area selectors; changing the company clears the area and loads only that company's areas.
- [ ] On area selection, request the preview. If there are no findings, show the reason and do not open a sendable modal. If no saved phone exists, open the modal with a blank destination field.
- [ ] Show a Bootstrap modal with an editable phone input and read-only message preview. Keep the phone override in client memory only.
- [ ] On confirmation, submit the signed preview token and phone with CSRF via `POST`; disable the button during submission to prevent duplicate clicks.
- [ ] Display gateway acceptance or a safe, actionable error in the modal; do not claim that acceptance means the recipient read the message.
- [ ] Add a superuser-only sidebar entry to the new page.
- [ ] Run `python manage.py check` and review the final diff for permission enforcement, CSRF, and absence of credentials in templates or JavaScript.
- [ ] Commit as `feat: agregar pantalla para enviar resumenes WhatsApp`.

### Task 5: Include a revocable public detail link in each WhatsApp

**Files:**
- Modify: `utiles/models.py`, `utiles/admin.py`, `utiles/views.py`, `utiles/urls.py`
- Create: `utiles/migrations/0002_enlacepublicohallazgos.py`
- Create: `templates/pages/utiles/hallazgos_publicos.html`
- Modify: `core_an/settings.py`, `.env.example`

- [ ] Persist a SHA-256 hash of a random bearer token, company and area scope, creation/expiration timestamps, and revocation timestamp; expire links after 14 days.
- [ ] Put the token in the URL fragment and fetch page data in a same-origin `Authorization: Bearer` request; return no sensitive data without a valid, unexpired, unrevoked token.
- [ ] Activate the token as part of the confirmed WhatsApp send, append its canonical HTTPS link to the message, and preserve the existing preview signature and idempotency reference.
- [ ] Render every overdue and next-five-day finding with full description, state, and due date, using the AN logo and a responsive read-only page.
- [ ] Expose superuser-only revocation in Django Admin; set no-store, no-referrer, and noindex headers on the public page and data endpoint.
- [ ] Apply the migration after a database backup and verify Django/Nginx configuration and HTTPS behavior.

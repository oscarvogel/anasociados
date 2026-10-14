"""Navigation for the authenticated AN portal.

The sidebar is intentionally curated here instead of being generated from
models registered in Django Admin. Menu visibility is a convenience only;
views remain responsible for enforcing access.
"""

from django.urls import reverse


MENU_GROUPS = (
    {
        "label": "",
        "standalone": True,
        "items": (
            {
                "label": "Tablero",
                "icon": "icon-home",
                "url_name": "index",
                "active_view_names": ("index",),
            },
        ),
    },
    {
        "label": "Seguridad e Higiene",
        "icon": "icon-alert-triangle",
        "items": (
            {
                "label": "Hallazgos",
                "icon": "icon-alert-triangle",
                "url_name": "syh:visualizar_movimientos",
                "active_view_names": (
                    "syh:visualizar_movimientos",
                    "syh:hallazgo_evidencias",
                    "syh:hallazgo_actualizar",
                    "syh:imprimir_movimientos",
                ),
            },
        ),
    },
    {
        "label": "",
        "standalone": True,
        "items": (
            {
                "label": "Alertas WhatsApp",
                "icon": "icon-message-circle",
                "url_name": "utiles:whatsapp_hallazgos",
                "superuser_only": True,
                "active_view_names": (
                    "utiles:whatsapp_hallazgos",
                    "utiles:whatsapp_hallazgos_areas",
                    "utiles:whatsapp_hallazgos_preview",
                    "utiles:whatsapp_hallazgos_send",
                ),
            },
        ),
    },
    {
        "label": "Usuarios",
        "icon": "icon-users",
        "items": (
            {
                "label": "Gestión de usuarios",
                "icon": "icon-user-check",
                "url_name": "usuarios:management_users",
                "superuser_only": True,
                "active_view_names": (
                    "usuarios:management_users",
                    "usuarios:management_user_create",
                    "usuarios:management_user_edit",
                ),
            },
            {
                "label": "Mi perfil",
                "icon": "icon-user",
                "url_name": "usuarios:update_user",
                "non_superuser_only": True,
                "active_view_names": ("usuarios:update_user",),
            },
            {
                "label": "Informes de accesos",
                "icon": "icon-bar-chart-2",
                "url_name": "usuarios:reporte_accesos",
                "superuser_only": True,
                "active_view_names": ("usuarios:reporte_accesos",),
            },
        ),
    },
    {
        "label": "Móviles",
        "icon": "icon-truck",
        "items": (
            {
                "label": "Tipos de vencimiento",
                "icon": "icon-calendar",
                "url_name": "moviles:tipo_vencimientos_list",
                "active_view_names": ("moviles:tipo_vencimientos_list",),
            },
            {
                "label": "Listado de móviles",
                "icon": "icon-truck",
                "url_name": "moviles:moviles_list",
                "active_view_names": ("moviles:moviles_list",),
            },
            {
                "label": "Personal",
                "icon": "icon-users",
                "url_name": "moviles:personal_list",
                "superuser_only": True,
                "active_view_names": ("moviles:personal_list",),
            },
            {
                "label": "Vencimientos de móviles",
                "icon": "icon-clock",
                "url_name": "moviles:vencimientos_list",
                "active_view_names": ("moviles:vencimientos_list",),
            },
            {
                "label": "Gastos de móviles",
                "icon": "icon-dollar-sign",
                "url_name": "moviles:gastos_movil_list",
                "active_view_names": ("moviles:gastos_movil_list",),
            },
            {
                "label": "Viajes",
                "icon": "icon-map",
                "url_name": "moviles:viajes_list",
                "active_view_names": (
                    "moviles:viajes_list",
                    "moviles:viajes_graficos",
                ),
            },
            {
                "label": "Carga de combustible",
                "icon": "icon-droplet",
                "url_name": "moviles:carga_combustible_list",
                "active_view_names": ("moviles:carga_combustible_list",),
            },
            {
                "label": "Matafuegos",
                "icon": "icon-shield",
                "url_name": "moviles:matafuegos_list",
                "active_view_names": ("moviles:matafuegos_list",),
            },
        ),
    },
    {
        "label": "Informes",
        "icon": "icon-bar-chart-2",
        "items": (
            {
                "label": "Excesos de velocidad",
                "icon": "icon-alert-triangle",
                "url_name": "syh:excesos_plantilla",
                "active_view_names": ("syh:excesos_plantilla",),
            },
            {
                "label": "Resumen mensual",
                "icon": "icon-file-text",
                "url_name": "syh:generar_resumen_mensual",
                "active_view_names": ("syh:generar_resumen_mensual",),
            },
            {
                "label": "Consumo de combustible",
                "icon": "icon-droplet",
                "url_name": "moviles:consumo_combustible_por_mes",
                "active_view_names": (
                    "moviles:consumo_combustible_por_mes",
                    "moviles:datos_consumo_combustible",
                ),
            },
            {
                "label": "Reporte de gastos",
                "icon": "icon-dollar-sign",
                "url_name": "moviles:reporte_gastos_movil",
                "superuser_only": True,
                "active_view_names": ("moviles:reporte_gastos_movil",),
            },
        ),
    },
)


def navigation_context(request):
    """Return only the curated navigation links available to this user."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"navigation_groups": []}

    current_view = getattr(getattr(request, "resolver_match", None), "view_name", None)
    navigation_groups = []

    for group in MENU_GROUPS:
        visible_items = []
        for item in group["items"]:
            if item.get("superuser_only") and not user.is_superuser:
                continue
            if item.get("non_superuser_only") and user.is_superuser:
                continue

            active_view_names = item.get("active_view_names", (item["url_name"],))
            visible_items.append(
                {
                    "label": item["label"],
                    "url": reverse(item["url_name"]),
                    "icon": item["icon"],
                    "is_active": current_view in active_view_names,
                    "search_text": f"{group['label']} {item['label']}".strip(),
                }
            )

        if not visible_items:
            continue

        navigation_groups.append(
            {
                "label": group["label"],
                "icon": group.get("icon", "icon-box"),
                "standalone": group.get("standalone", False),
                "is_active": any(item["is_active"] for item in visible_items),
                "items": visible_items,
            }
        )

    return {"navigation_groups": navigation_groups}

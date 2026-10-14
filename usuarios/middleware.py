from .models import UsuarioMenuAcceso


MENU_LABELS = {
    "index": "Tablero",
    # "Hallazgos" es la pantalla de trabajo y va al primer nivel del menu,
    # no dentro de Informes. La etiqueta se actualizo para que el reporte de
    # accesos no la siga contando como un informe.
    "syh:visualizar_movimientos": "Hallazgos",
    "syh:excesos_plantilla": "Informes - Excesos de Velocidad",
    "syh:generar_resumen_mensual": "Informes - Resumen Mensual",
    "moviles:consumo_combustible_por_mes": "Informes - Consumo de Combustible",
    "moviles:reporte_gastos_movil": "Informes - Reporte de gastos",
    "moviles:tipo_vencimientos_list": "Moviles - Tipos de vencimiento",
    "moviles:moviles_list": "Moviles - Listado",
    "moviles:personal_list": "Moviles - Personal",
    "moviles:vencimientos_list": "Moviles - Vencimientos Moviles",
    "moviles:gastos_movil_list": "Moviles - Gastos de Moviles",
    "moviles:viajes_list": "Moviles - Lista de Viajes",
    "moviles:matafuegos_list": "Matafuegos - Listado de Matafuegos",
    "usuarios:update_user": "Perfil",
    "usuarios:reporte_accesos": "Administracion - Reporte de accesos",
}


class MenuAccessTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method != "GET" or not request.user.is_authenticated:
            return response

        resolver_match = getattr(request, "resolver_match", None)
        if not resolver_match:
            return response

        view_name = resolver_match.view_name or ""
        menu_nombre = MENU_LABELS.get(view_name)

        # Solo registramos rutas de navegación del sistema (evita ruido de recursos internos).
        if not menu_nombre:
            return response

        UsuarioMenuAcceso.objects.create(
            user=request.user,
            menu_codigo=view_name,
            menu_nombre=menu_nombre,
            path=request.path,
        )
        return response

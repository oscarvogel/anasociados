from django.urls import path

from utiles import views

app_name = "utiles"

urlpatterns = [
    path("hallazgos-publicos/", views.hallazgos_publicos_page, name="hallazgos_publicos"),
    path("hallazgos-publicos/datos/", views.hallazgos_publicos_datos, name="hallazgos_publicos_datos"),
    path("hallazgos-publicos/subir/", views.hallazgos_publicos_subir, name="hallazgos_publicos_subir"),

    # Bandeja de revision del administrador. Mismo alcance que el enlace del
    # responsable, otro token: este es el que habilita ver las fotos y a
    # cerrar o reabrir hallazgos.
    path("evidencias-revision/", views.evidencias_revision_page, name="evidencias_revision_page"),
    path("evidencias-revision/datos/", views.evidencias_revision_datos, name="evidencias_revision_datos"),
    path("evidencias-revision/imagen/<int:evidencia_id>/", views.evidencias_revision_imagen, name="evidencias_revision_imagen"),
    path("evidencias-revision/responder/", views.evidencias_revision_responder, name="evidencias_revision_responder"),
    path("whatsapp/hallazgos/", views.whatsapp_hallazgos_page, name="whatsapp_hallazgos"),
    path("whatsapp/hallazgos/areas/", views.whatsapp_hallazgos_areas, name="whatsapp_hallazgos_areas"),
    path("whatsapp/hallazgos/preview/", views.whatsapp_hallazgos_preview, name="whatsapp_hallazgos_preview"),
    path("whatsapp/hallazgos/enviar/", views.whatsapp_hallazgos_send, name="whatsapp_hallazgos_send"),
]

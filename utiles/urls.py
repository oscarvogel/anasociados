from django.urls import path

from utiles import views

app_name = "utiles"

urlpatterns = [
    path("whatsapp/hallazgos/", views.whatsapp_hallazgos_page, name="whatsapp_hallazgos"),
    path("whatsapp/hallazgos/areas/", views.whatsapp_hallazgos_areas, name="whatsapp_hallazgos_areas"),
    path("whatsapp/hallazgos/preview/", views.whatsapp_hallazgos_preview, name="whatsapp_hallazgos_preview"),
    path("whatsapp/hallazgos/enviar/", views.whatsapp_hallazgos_send, name="whatsapp_hallazgos_send"),
]

from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("organizacion/", views.onboarding_organizacion, name="onboarding_organizacion"),
    path("organizacion/plantillas/", views.onboarding_plantillas, name="onboarding_plantillas"),
    path("arco/", views.arco_lista, name="arco_lista"),
    path("arco/<uuid:pk>/", views.arco_detalle, name="arco_detalle"),
    path("solicitudes-arco/nueva/", views.arco_publica_nueva, name="arco_publica_nueva"),
    path(
        "solicitudes-arco/<uuid:pk>/confirmacion/",
        views.arco_publica_confirmacion,
        name="arco_publica_confirmacion",
    ),
]

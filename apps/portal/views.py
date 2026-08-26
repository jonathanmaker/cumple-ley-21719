from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.arco.models import SolicitudArco
from apps.auditoria.models import AuditLog
from apps.consentimiento.models import RegistroConsentimiento
from apps.integraciones.models import WebhookSuscripcion
from apps.integraciones.webhooks import disparar_webhook
from apps.organizacion.models import Organizacion
from apps.rat.models import ActividadTratamiento, PlantillaProceso
from apps.titulares.models import Titular

from .forms import OrganizacionForm, ResolverArcoForm, SeleccionPlantillasForm, SolicitudArcoPublicaForm


@login_required
def dashboard(request):
    contexto = {
        "organizacion": Organizacion.objects.first(),
        "actividades_activas": ActividadTratamiento.objects.filter(activa=True).count(),
        "consentimientos_otorgados": RegistroConsentimiento.objects.filter(
            estado=RegistroConsentimiento.Estado.OTORGADO
        ).count(),
        "arco_pendientes": SolicitudArco.objects.filter(
            estado__in=[SolicitudArco.Estado.PENDIENTE, SolicitudArco.Estado.EN_PROCESO]
        ).order_by("fecha_limite")[:10],
        "ultimos_eventos": AuditLog.objects.all()[:10],
    }
    return render(request, "portal/dashboard.html", contexto)


@login_required
def onboarding_organizacion(request):
    """Paso 1 del wizard: datos de la entidad responsable del tratamiento."""
    organizacion = Organizacion.objects.first()
    if request.method == "POST":
        form = OrganizacionForm(request.POST, instance=organizacion)
        if form.is_valid():
            form.save()
            return redirect("portal:onboarding_plantillas")
    else:
        form = OrganizacionForm(instance=organizacion)
    return render(request, "portal/onboarding_organizacion.html", {"form": form})


@login_required
def onboarding_plantillas(request):
    """Paso 2 del wizard: elegir procesos (CTX-002 §2.A) y generar el RAT inicial."""
    if request.method == "POST":
        form = SeleccionPlantillasForm(request.POST)
        if form.is_valid():
            for plantilla in form.cleaned_data["plantillas"]:
                ActividadTratamiento.objects.get_or_create(
                    plantilla_origen=plantilla,
                    defaults={
                        "nombre": plantilla.nombre,
                        "finalidad": plantilla.descripcion or plantilla.nombre,
                        "base_licitud": plantilla.base_licitud_sugerida,
                        "plazo_conservacion_meses": plantilla.plazo_sugerido_meses or 12,
                    },
                )
            return redirect("portal:dashboard")
    else:
        form = SeleccionPlantillasForm()
    return render(
        request,
        "portal/onboarding_plantillas.html",
        {"form": form, "plantillas": PlantillaProceso.objects.all()},
    )


@login_required
def arco_lista(request):
    solicitudes = SolicitudArco.objects.all().order_by("fecha_limite")
    estado = request.GET.get("estado")
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    return render(
        request,
        "portal/arco_lista.html",
        {"solicitudes": solicitudes, "estados": SolicitudArco.Estado.choices, "ahora": timezone.now()},
    )


@login_required
def arco_detalle(request, pk):
    solicitud = get_object_or_404(SolicitudArco, pk=pk)
    if request.method == "POST":
        estado_anterior = solicitud.estado
        form = ResolverArcoForm(request.POST, instance=solicitud)
        if form.is_valid():
            solicitud = form.save(commit=False)
            if (
                solicitud.estado in (SolicitudArco.Estado.RESUELTA, SolicitudArco.Estado.RECHAZADA)
                and estado_anterior != solicitud.estado
            ):
                solicitud.fecha_resolucion = timezone.now()
            solicitud.save()
            AuditLog.objects.create(
                usuario=request.user,
                modulo="ARCO",
                accion=AuditLog.Accion.MODIFICACION,
                descripcion=f"Solicitud ARCO {solicitud.id} pasó a estado {solicitud.estado} ({request.user.get_username()}).",
            )
            if solicitud.estado == SolicitudArco.Estado.RESUELTA:
                disparar_webhook(
                    WebhookSuscripcion.Evento.ARCO_RESUELTA,
                    {
                        "solicitud_id": str(solicitud.id),
                        "titular_id": str(solicitud.titular_id),
                        "tipo_derecho": solicitud.tipo_derecho,
                        "fecha_resolucion": solicitud.fecha_resolucion.isoformat(),
                    },
                )
            return redirect("portal:arco_lista")
    else:
        form = ResolverArcoForm(instance=solicitud)
    return render(request, "portal/arco_detalle.html", {"solicitud": solicitud, "form": form})


def arco_publica_nueva(request):
    """Formulario público (sin login): canal de entrada para PYMEs que no
    tienen un sistema legado integrado vía API (CTX-003 §2).
    """
    if request.method == "POST":
        form = SolicitudArcoPublicaForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            rut_hash = Titular.hash_rut(datos["rut"])
            titular = Titular.objects.filter(rut_hash=rut_hash).first() or Titular()
            titular.nombre = datos["nombre"]
            titular.email = datos["email"]
            titular.tipo_titular = titular.tipo_titular or Titular.TipoTitular.CLIENTE
            titular.rut = datos["rut"]
            titular.save()
            solicitud = SolicitudArco.objects.create(
                titular=titular, tipo_derecho=datos["tipo_derecho"], canal_ingreso="WEB_PUBLICO"
            )
            return redirect("portal:arco_publica_confirmacion", pk=solicitud.pk)
    else:
        form = SolicitudArcoPublicaForm()
    return render(request, "portal/arco_publica_nueva.html", {"form": form})


def arco_publica_confirmacion(request, pk):
    solicitud = get_object_or_404(SolicitudArco, pk=pk)
    return render(request, "portal/arco_publica_confirmacion.html", {"solicitud": solicitud})

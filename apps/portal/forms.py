from django import forms

from apps.arco.models import SolicitudArco
from apps.organizacion.models import Organizacion
from apps.rat.models import PlantillaProceso


class OrganizacionForm(forms.ModelForm):
    class Meta:
        model = Organizacion
        fields = ["razon_social", "rut", "rubro", "direccion", "dpd_nombre", "dpd_contacto"]


class SeleccionPlantillasForm(forms.Form):
    plantillas = forms.ModelMultipleChoiceField(
        queryset=PlantillaProceso.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )


class ResolverArcoForm(forms.ModelForm):
    class Meta:
        model = SolicitudArco
        fields = ["estado", "justificacion_rechazo"]
        widgets = {"justificacion_rechazo": forms.Textarea(attrs={"rows": 3})}


class SolicitudArcoPublicaForm(forms.Form):
    rut = forms.CharField(max_length=20, label="RUT")
    nombre = forms.CharField(max_length=255, label="Nombre completo")
    email = forms.EmailField(label="Correo electrónico")
    tipo_derecho = forms.ChoiceField(
        choices=SolicitudArco.TipoDerecho.choices, label="¿Qué derecho deseas ejercer?"
    )

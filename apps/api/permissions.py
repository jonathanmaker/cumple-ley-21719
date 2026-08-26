from rest_framework import permissions


class TieneScope(permissions.BasePermission):
    """Requiere una API key válida (request.auth) y, si la vista declara un
    atributo `scope_requerido`, que ese scope esté en SistemaIntegrado.scopes.

    Deny-by-default: sin API key válida, no hay acceso — sin importar si la
    vista definió o no un scope específico.
    """

    def has_permission(self, request, view):
        sistema = request.auth
        if sistema is None:
            return False
        requerido = getattr(view, "scope_requerido", None)
        return requerido is None or requerido in sistema.scopes

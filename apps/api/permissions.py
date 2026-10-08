def has_permission(self, request, view):
    sistema = request.auth
    if sistema is None:
        return False
    requerido = getattr(view, "scope_requerido", None)
    if not requerido or not isinstance(requerido, str):
        return False  # Deny-by-default: sin scope explícito, no hay acceso
    return requerido in sistema.scopes
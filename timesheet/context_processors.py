from .views import can_access_employee_features, is_admin


def role_flags(request):
    """Expose common role flags to templates."""
    user = request.user
    if not user.is_authenticated:
        return {
            'is_admin_user': False,
            'can_access_employee_features': False,
        }

    return {
        'is_admin_user': is_admin(user),
        'can_access_employee_features': can_access_employee_features(user),
    }

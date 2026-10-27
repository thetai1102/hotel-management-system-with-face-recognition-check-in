def user_roles(request):
    """
    Provide user role variables to all templates.
    Cung cấp biến quyền user cho tất cả template.
    """

    is_admin_role = False
    is_receptionist_role = False

    if request.user.is_authenticated:
        is_admin_role = (
            request.user.is_superuser or
            request.user.groups.filter(name='Admin').exists()
        )

        is_receptionist_role = request.user.groups.filter(
            name='Receptionist'
        ).exists()

    return {
        'is_admin_role': is_admin_role,
        'is_receptionist_role': is_receptionist_role,
    }
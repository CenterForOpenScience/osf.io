
def setInstitution(request):
    now_user = request.user
    if now_user.is_superuser:
        institutions_name_text = ''
    elif now_user.is_staff and not now_user.is_superuser:
        now_institutions_name = list(now_user.affiliated_institutions.all().values_list('name', flat=True))
        if len(now_institutions_name) > 0:
            institutions_name_text = now_institutions_name[0]
        else:
            institutions_name_text = ''
    else:
        institutions_name_text = ''
    return {'institution_name': institutions_name_text}

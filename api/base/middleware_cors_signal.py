def cors_allow_institution_domains(sender, request, *args, **kwargs):
    if not request.COOKIES:
        if request.META.get('HTTP_AUTHORIZATION'):
            return True
        elif (
                request.method == 'OPTIONS' and
                'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in request.META and
                'authorization' in [
                    h.strip() for h in request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '').split(',')
                ]
        ):
            return True
    return False

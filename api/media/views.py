from osf.utils.storage import BannerImage

from api.base.utils import get_object_or_error

from django.db.models import Q
from django.http import FileResponse
from django.core.files.base import ContentFile
from django.views.decorators.http import require_GET


@require_GET
#TODO: Move to api/banners
def get_media(request, filename, **kwargs):
    banner_image = get_object_or_error(BannerImage, Q(filename=filename), request)
    response = FileResponse(ContentFile(banner_image.image))
    response['Content-Type'] = 'image/svg+xml'
    return response

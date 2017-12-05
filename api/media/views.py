import os

from api.base import settings
from rest_framework import generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from api.media.permissions import IsAdminOrFromAdminApp

#TODO: CHANGE STORAGE SOLUTION
def save_media_file(file_obj, filename):
    file_path = os.path.join(settings.STATIC_FOLDER, filename)

    with open(file_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)

def delete_media_file(filename):
    file_path = os.path.join(settings.STATIC_FOLDER, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)

class FileUploadView(generics.views.APIView):
    parser_classes = (FileUploadParser,)

    permission_classes = (
        IsAdminOrFromAdminApp,
    )

    def put(self, request, filename, format=None, **kwargs):
        file_obj = request.data['file']
        save_media_file(file_obj, filename)

        return Response(status=204)

    def delete(self, request, filename, **kwargs):
        delete_media_file(filename)

        return Response(status=204)

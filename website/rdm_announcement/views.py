# -*- coding: utf-8 -*-

from osf.models.rdm_announcement import RdmFcmDevice
from osf.models.base import Guid

def update_user_token(**kwargs):
    uid = kwargs.get('uid')
    token = kwargs.get('token')
    success = "False"
    if Guid.objects.filter(_id=uid).exists() and token != None:
        obj = Guid.objects.get(_id=uid)
        user_id = getattr(obj, "object_id")
        if RdmFcmDevice.objects.filter(device_token=token).exists():
            RdmFcmDevice.objects.filter(device_token=token).update(user_id=user_id)
        else:
            RdmFcmDevice.objects.create(user_id=user_id, device_token=token).save()
        success = "True"

    return {
        'success': success,
    }


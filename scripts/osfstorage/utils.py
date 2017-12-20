#!/usr/bin/env python
# encoding: utf-8

import os
import glob
import hashlib
import subprocess

import boto3

from scripts.osfstorage import settings as storage_settings


def sha256(file_path, chunk_size=4194304):  # 4MB
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_parity_files(file_path, redundancy=5):
    """
    :raise: `ParchiveError` if creation of parity files fails
    """
    try:
        stat = os.stat(file_path)
        if not stat.st_size:
            return []
    except OSError as error:
        raise Exception('Could not read file: {0}'.format(error.strerror))
    path, name = os.path.split(file_path)
    with open(os.devnull, 'wb') as DEVNULL:
        args = [
            'par2',
            'c',
            '-r{0}'.format(redundancy),
            os.path.join(path, '{0}.par2'.format(name)),
            file_path,
        ]

        ret_code = subprocess.call(args, stdout=DEVNULL, stderr=DEVNULL)

        if ret_code != 0:
            raise Exception('{0} failed with code {1}'.format(' '.join(args), ret_code))

        paths = [
            os.path.abspath(p)
            for p in
            glob.glob(os.path.join(path, '{0}*.par2'.format(name)))
        ]
        return [(p, sha256(p)) for p in paths]


def get_glacier_client():
    return boto3.client(
        'glacier',
        aws_access_key_id=storage_settings.AWS_ACCESS_KEY,
        aws_secret_access_key=storage_settings.AWS_SECRET_KEY,
        region_name=storage_settings.AWS_REGION
    )


def get_glacier_resource():
    return boto3.resource(
        'glacier',
        aws_access_key_id=storage_settings.AWS_ACCESS_KEY,
        aws_secret_access_key=storage_settings.AWS_SECRET_KEY,
        region_name=storage_settings.AWS_REGION
    )

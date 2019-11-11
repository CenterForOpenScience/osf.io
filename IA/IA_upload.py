import os
import argparse
import requests
import boto
from boto.s3.connection import S3Connection, OrdinaryCallingFormat
import asyncio
import xmltodict
from io import BytesIO
import secrets

CHUNK_SIZE = 1000
OSF_API_URI = 'http://localhost:8000/'
OSF_COLLECTION_NAME = 'cos-dev-sandbox'

HERE = os.path.dirname(os.path.abspath(__file__))


class IAException(Exception):
    pass


def mp_from_ids(mp_id, mp_keyname, bucket):
    mp = boto.s3.multipart.MultiPartUpload(bucket)
    mp.key_name = mp_keyname
    mp.id = mp_id
    return mp


async def gather_and_upload(bucket_name, parent):
    tasks = []

    for root, dirs, files in os.walk(parent):
        for file in files:
            path = os.path.join(root, file)
            with open(path, 'rb') as fp:
                data = fp.read()
                size = len(data)
                if size > CHUNK_SIZE:
                    tasks.append(chunked_upload(bucket_name, path, data))
                else:
                    tasks.append(upload(bucket_name, path, data))

    return await asyncio.gather(*tasks)


async def upload(bucket_name, filename, file_content):
    headers = {
        'authorization': 'LOW {}:{}'.format(secrets.IA_ACCESS_KEY, secrets.IA_SECRET_KEY),
        'x-amz-auto-make-bucket': '1',
        'Content-Type': 'application/octet-stream',
        'x-archive-meta01-collection': OSF_COLLECTION_NAME
    }
    url = 'http://s3.us.archive.org/{}/{}'.format(bucket_name, filename)
    resp = requests.put(url, headers=headers, data=file_content, stream=True)

    if resp.status_code != 200:
        error_json = dict(xmltodict.parse(resp.content))
        raise IAException(error_json)

    return resp


async def chunked_upload(bucket_name, filename, file_content):
    conn = boto.connect_s3(
        secrets.IA_ACCESS_KEY,
        secrets.IA_SECRET_KEY,
        host='s3.us.archive.org',
        is_secure=False,
        calling_format=OrdinaryCallingFormat()
    )
    bucket = conn.lookup(bucket_name)
    mp = bucket.initiate_multipart_upload(filename)

    tasks = []
    chunks = [file_content[i:i + CHUNK_SIZE] for i in range(0, len(file_content), CHUNK_SIZE)]

    for i, chunk in enumerate(chunks):
        mp = mp_from_ids(mp.id, filename, bucket)
        upload_part_from_file = asyncio.coroutine(mp.upload_part_from_file)
        tasks.append(asyncio.ensure_future(upload_part_from_file(BytesIO(chunk), i + 1)))

    return await asyncio.gather(*tasks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-b',
        '--bucket',
        help='The name of the bucket you want to dump in.',
        required=True
    )
    parser.add_argument(
        '-s',
        '--source',
        help='The name of the folder you want to dump.',
        required=True
    )
    args = parser.parse_args()
    bucket = args.bucket
    source = args.source

    asyncio.run(gather_and_upload(bucket, source))

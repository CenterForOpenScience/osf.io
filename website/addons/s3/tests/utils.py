import mock
import random
from website.addons.s3.api import S3Wrapper,S3Key


def create_mock_s3(bucket_name='to-kill-a-mocking-bucket'):
    mock_s3 = mock.create_autospec(S3Wrapper)
    mock_s3.get_bucket_name.return_value = bucket_name



	mock_s3.get_cors_rules.return_value = """<?xml version="1.0" encoding="UTF-8"?>
	<CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
	    <CORSRule>
	        <AllowedOrigin>*</AllowedOrigin>
	        <AllowedMethod>PUT</AllowedMethod>
	        <MaxAgeSeconds>3000</MaxAgeSeconds>
	        <AllowedHeader>Authorization</AllowedHeader>
	        <AllowedHeader>Content-Type</AllowedHeader>
	        <AllowedHeader>x-amz-acl</AllowedHeader>
	        <AllowedHeader>origin</AllowedHeader>
	    </CORSRule>
	    <CORSRule>
            <AllowedOrigin>*</AllowedOrigin>
            <AllowedMethod>POST</AllowedMethod>
            <AllowedHeader>origin</AllowedHeader>
            <AllowedHeader>Content-Type</AllowedHeader>
            <AllowedHeader>x-amz-acl</AllowedHeader>
	        <AllowedHeader>Authorization</AllowedHeader>
	    </CORSRule>
	'</CORSConfiguration>"""


def create_mock_key():
    mock_key = mock.create_autospec(S3Key)



def _random_string(length):
   return ''.join(random.choice(string.lowercase) for i in range(length))

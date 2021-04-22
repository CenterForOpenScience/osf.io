# RDM S3 Compatible Boto3 Storage Addon

S3 Compatible Storage Addon enables to mount Cloud Storage which supports Amazon S3-like API on the project.

## Configuring the addon

Users can select storage from the S3 Compatible Storage List,
which is defined in `addons/s3compat/static/settings.json`.

```
{
    "availableServices": [{"name": "Wasabi",
                           "host": "s3.wasabisys.com",
                           "bucketLocations": {
                             "us-east": {"name": "us-east", "host": "s3.wasabisys.com"},
                             "us-west-1": {"name": "us-west-1", "host": "s3.us-west-1.wasabisys.com"},
                             "eu-central": {"name": "eu-central", "host": "s3.eu-central-1.wasabisys.com"},
                             "": {"name": "Virginia"}}},
                          {"name": "My Private Storage",
                           "host": "my-private-storage-address:80"}
                           ],
    "encryptUploads": true
}
```

## Enabling the addon

### Enable on RDM
1. On RDM, enable S3 Compatible Storage as a provider
2. Scroll down to Configure Add-ons
3. Choose desired storage service
4. Connect your account and enter your ID and secret
5. Select a bucket to work from, or create a new one.

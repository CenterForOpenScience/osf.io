# OSF S3 Compatible Storage Addon

S3 Compatible Storage Addon enables to mount Cloud Storage which supports Amazon S3-like API on the project.

## Configuring the addons

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

### Enable on OSF
1. On osf, enable S3 as a provider
2. Scroll down to Configure Add-ons
3. Connect your account and enter your ID and secret
4. Select a bucket to work from, or create a new one.

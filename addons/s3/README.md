# OSF Amazon S3 Addon


## Enabling the addon for development

### Obtain an access ID and secret from Amazon web services
If you already have an access key and ID, skip this step
1. Go to amazon webservices
2. Log into your console
3. Click on your username go to "My Security Credentials"
4. Go to "Access Keys" and click on "Create New Access Key"
5. Download your access ID/secret pair

### Enable on OSF
1. On osf, enable S3 as a provider
2. Scroll down to Configure Add-ons
3. Connect your account and enter your ID and secret
4. Select a bucket to work from, or create a new one.


## Creating a restricted-access AWS user for S3 connection

1. Login to AWS
2. Open Identity and Access Management
3. Create a user, assign name, set "Access Type" to "Programmatic Access"
4. Permissions (simple):
   1. Add "AmazonS3FullAccess" policy
5. Permissions (minimal):
   1. Click "Create Policy" => opens a new window
   2. Make a new policy with the following Actions enabled: `["s3:DeleteObject", "s3:GetObject", "s3:ListBucket", "s3:PutObject", "s3:ReplicateObject", "s3:RestoreObject", "s3:ListAllMyBuckets", "s3:GetBucketLocation", "s3:CreateBucket"]`
   3. Resources: *I just do "All Resources", but an AWS-educated person would know better about how to narrow it down.
   4. Click "Create"
   5. Return to "Create User" window
   6. Reload policy list
   7. Search for your new policy and select.
6. Tags: *eh*
7. Click "Review", review, then click "Create user"
8. Note "Access key ID" and "Secret access key".  These are the inputs to the OSF S3 addon.

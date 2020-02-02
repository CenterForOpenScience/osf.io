## Setting up Chronos locally

In order to access Chronos's staging server to test Chronos locally one must do a number of things.

1. Enter or sync the osfio_preprints_1 container and set config/environment.js to include the desired preprint provider in the `chronosProviders`
list.

2. Make sure that your desired journal has an id listed in config/environment.js's approvedChronosJournalIds, or create a new journal and add that to the list.

3. Go to website/settings/local.py and add the following

VERIFY_CHRONOS_SSL_CERT = False
CHRONOS_USE_FAKE_FILE = True
CHRONOS_FAKE_FILE_URL = <any publicly accessible file I used https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/TERMS_OF_USE.md>
CHRONOS_HOST = 'https://staging-api.chronos-oa.com'
CHRONOS_USERNAME = <ask a dev for staging creds to put here>
CHRONOS_PASSWORD =  <ask a dev for staging creds to put here>
CHRONOS_API_KEY =  <ask a dev for staging creds to put here>

The link 'Submit to an APA-published journal' should appear when looking at a accepted preprint in the provider you've added to config/environment.js.

# OSF figshare Addon

## Setup figshare for development

**Note:** The figshare account you test with **cannot** be the same as the figshare account
associated with the API application. Attempting to use the same account will result in errors
akin to *{"error": "You cannot request an access token for yourself!"}* (This note may be outdated,
as figshare updated their original API.) If you set up your figshare access with a "Personal Token", this should not be an issue.


### Manual generation of auth token and ExternalAccount

1. Go to [figshare](http://figshare.com), create an account, and login
2. Click the dropdown with your name and select "Applications". Scroll down to the bottom of the page and click ""Create Personal Token"
3. Make a note of your personal token.
4. Navigate to your osf.io repo location and run `docker-compose run --rm web invoke shell`, then run:
```python
from addons.figshare.client import FigshareClient
from osf.models.user import OSFUser
from osf.models import ExternalAccount

me = OSFUser.load('<osf_guid>')
token = '<personal token id from figshare>'
client = FigshareClient(token)

info = client.userinfo()
ea = ExternalAccount(
    provider='figshare',
    provider_id=info['id'],
    provider_name='figshare',
    oauth_key=token,
    display_name='{} {}'.format(info['first_name'], info['last_name'])
)
ea.save()
fu = me.get_or_add_addon('figshare')
me.external_accounts.add(ea)
me.save()

commit()
```
5. Done. At this point, you should be able to enable figshare on a node and import the account you just created.
6. Enable your new provider


### OAuth and ngrok (alternate untested instructions)
**Note:** It is reccomended that you follow the above instructions over the ngrok insturctions.

1. Download ngrok (partially free, but TLS requires [subscription](https://ngrok.com/product#pricing))
2. Run with `ngrok tls -subdomain=openscience 5000`
  * `-subdomain` can be something other than `openscience`
  * this assumes you have the OSF running with https enabled
3. Copy addons/figshare/settings/defaults.py to addons/figshare/settings/local.py
4. Go to [figshare](http://figshare.com), create an account, and login
5. Click the dropdown with your name and select **Applications** and click **Create application**
6. Add https://openscience.ngrok.io:5000/api/v1/oauth/callback/figshare/ as the **Callback URL**
7. Open addons/figshare/settings/local.py
  * Copy the *consumer_key* to **CLIENT_ID**
  * Copy the *consumer_secret* to **CLIENT_SECRET**

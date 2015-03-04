## Setup FigShare for development

**Note:** The FigShare account you test with **cannot** be the same as the FigShare account
associated with the API application. Attempting to use the same account will result in errors
akin to *{"error": "You cannot request an access token for yourself!"}*

1. Copy website/addons/figshare/settings/defaults.py to website/addons/figshare/settings/local.py
2. Go to the [FigShare website](http://figshare.com)
3. *(Optional)* Create an account
4. Login to your account
5. Click the dropdown with your name and select **Applications**
6. Click the **Projects** tab
7. Click **Create a new application**
8. Add http://127.0.0.1:5000/api/v1/addons/figshare/callback/ as the **Application URL**
9. Look for your newly created application in *My applications* and click **View/Edit**
10. Click the *Access codes* tab
11. Open website/addons/figshare/settings/local.py
  1. Copy the *consumer_key* to **CLIENT_ID**
  2. Copy the *consumer_secret* to **CLIENT_SECRET**
12. Open website/settings/local.py
  3. Add *figshare* to ADDONS_REQUESTED
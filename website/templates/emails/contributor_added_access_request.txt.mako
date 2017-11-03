<%!
    from website import settings
%>

Hello ${user.fullname},

${referrer_name + ' has approved your access request and added you' if referrer_name else 'Your access request has been approved, and you have been added'} as a contributor to the project "${node.title}" on the Open Science Framework: ${node.absolute_url}

You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '} notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}


Sincerely,

The OSF Team

Center for Open Science

210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903-5083

Privacy Policy: https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md

More information? Visit https://osf.io/ and https://cos.io/ for information about the Open Science Framework and its supporting organization, the Center for Open Science.

Questions? Email contact@osf.io

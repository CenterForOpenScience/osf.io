<%!
    from website import settings
%>

Hello ${user.fullname},

${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the project "${node.title}" on the Open Science Framework: ${node.absolute_url}

This project also has a public preprint, discoverable at: ${node.preprints.get_queryset()[0].absolute_url}

You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '} notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}

If you are erroneously being associated with "${node.title}," then you may visit the project's "Contributors" page and remove yourself as a contributor.


Sincerely,

Open Science Framework Robot

Center for Open Science

210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903-5083

Privacy Policy: https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md



Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.

Questions? Email ${osf_contact_email}

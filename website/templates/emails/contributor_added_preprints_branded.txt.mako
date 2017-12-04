<%!
    from website import settings
%>

Hello ${user.fullname},

${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the ${branded_service.preprint_word} "${node.title}" on ${branded_service.name}, which is hosted on the Open Science Framework: ${node.absolute_url}

You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this ${branded_service.preprint_word}. Each ${branded_service.preprint_word} is associated with a project on the Open Science Framework for managing the ${branded_service.preprint_word}. To change your email notification preferences, visit your project user settings: ${settings.DOMAIN + "settings/notifications/"}

If you have been erroneously associated with "${node.title}", then you may visit the project's "Contributors" page and remove yourself as a contributor.


Sincerely,

Your ${branded_service.name} and OSF teams


Center for Open Science

210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903-5083

Privacy Policy: https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md


Want more information? Visit https://osf.io/preprints/${branded_service._id} to learn about ${branded_service.name} or https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.

Questions? Email support+${branded_service._id}@osf.io

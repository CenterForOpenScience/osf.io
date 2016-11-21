<%!
    from website import settings
%>

Hello ${user.fullname},

${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the preprint "${node.title}" on ${branded_service_name}, which is hosted on the Open Science Framework: ${node.absolute_url}

You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this preprint. Each preprint is associated with a project on the Open Science Framework for managing the preprint. To change your email notification preferences, visit your project user settings: ${settings.DOMAIN + "settings/notifications/"}

If you have been erroneously associated with "${node.title}", then you may visit the project's "Contributors" page and remove yourself as a contributor.


Sincerely,

Your ${branded_service_name} and OSF teams


Want more information? Visit https://osf.io/preprints/${branded_service_name.lower()} to learn about ${branded_service_name} or https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.

Questions? Email support+${branded_service_name.lower()}@osf.io

<%!
    from website import settings
%>

Hello ${user.fullname},

${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the project "${node.title}" on the Open Science Framework: ${node.absolute_url}

You will automatically be subscribed to notification emails for comments and updated files for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}

If you are erroneously being associated with "${node.title}," then you may visit the project's "Contributors" page and remove yourself as a contributor.


Sincerely,

Open Science Framework Robot


Want more information? Visit http://osf.io/ to learn about the Open Science Framework, or http://cos.io/ for information about its supporting organization, the Center for Open Science.

Questions? Email contact@osf.io

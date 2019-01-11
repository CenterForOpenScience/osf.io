<%!
    from website import settings
%>

Hello ${user.fullname},

${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the preprint "${node.title}" on the GakuNin RDM: ${node.absolute_url}

You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}

If you are erroneously being associated with "${node.title}," then you may visit the project's "Contributors" page and remove yourself as a contributor.


Sincerely,

GakuNin RDM Robot


National Institute of Informatics

2-1-2 Hitotsubashi, Chiyoda Ward, Tokyo 101-8430, JAPAN

Privacy Policy: https://meatwiki.nii.ac.jp/confluence/pages/viewpage.action?pageId=32676422


Want more information? Visit https://rdm.nii.ac.jp/ to learn about the GakuNin RDM, or https://nii.ac.jp/ for information about its supporting organization, the National Institute of Informatics.

Questions? Email contact@osf.io

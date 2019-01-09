<%!
    from website import settings
%>

Hello ${user.fullname},

${referrer_name + ' has added you' if referrer_name else 'You have been added'} as a contributor to the ${branded_service.preprint_word} "${node.title}" on ${branded_service.name}, which is hosted on the GakuNin RDM: ${node.absolute_url}

You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this ${branded_service.preprint_word}. Each ${branded_service.preprint_word} is associated with a project on the GakuNin RDM for managing the ${branded_service.preprint_word}. To change your email notification preferences, visit your project user settings: ${settings.DOMAIN + "settings/notifications/"}

If you have been erroneously associated with "${node.title}", then you may visit the project's "Contributors" page and remove yourself as a contributor.


Sincerely,

Your ${branded_service.name} and GakuNin RDM teams


National Institute of Informatics

2-1-2 Hitotsubashi, Chiyoda Ward, Tokyo 101-8430, JAPAN

Privacy Policy: https://meatwiki.nii.ac.jp/confluence/pages/viewpage.action?pageId=32676422


Want more information? Visit https://rdm.nii.ac.jp/preprints/${branded_service._id} to learn about ${branded_service.name} or https://rdm.nii.ac.jp/ to learn about the GakuNin RDM, or https://nii.ac.jp/ for information about its supporting organization, the National Institute of Informatics.

Questions? Email support+${branded_service._id}@osf.io

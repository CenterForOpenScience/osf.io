<%!
    from website import settings
%>

Hello ${fullname},

You have been added by ${referrer.fullname} as a contributor to the project "${node.title}" on the GakuNin RDM. To set a password for your account, visit:

${claim_url}

Once you have set a password, you will be able to make contributions to "${node.title}" and create your own projects. You will automatically be subscribed to notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}

To preview "${node.title}" click the following link: ${node.absolute_url}

(NOTE: if this project is private, you will not be able to view it until you have confirmed your account)

If you are not ${fullname} or you are erroneously being associated with "${node.title}" then email contact@osf.io with the subject line "Claiming Error" to report the problem.


Sincerely,

GakuNin RDM Robot


National Institute of Informatics

2-1-2 Hitotsubashi, Chiyoda Ward, Tokyo 101-8430, JAPAN

Privacy Policy: https://meatwiki.nii.ac.jp/confluence/pages/viewpage.action?pageId=32676422


Want more information? Visit https://rdm.nii.ac.jp/ to learn about the GakuNin RDM, or https://nii.ac.jp/ for information about its supporting organization, the National Institute of Informatics.

Questions? Email contact@osf.io

<%!
    from website import settings
%>

Hello ${fullname},

You have been added by ${referrer.fullname} as a contributor to the project "${node.title}" on the Open Science Framework. To set a password for your account, visit:

${claim_url}

Once you have set a password, you will be able to make contributions to ${node.title} and create your own projects. You will automatically be subscribed to notification emails for updates to this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}

If you are not ${fullname} or you are erroneously being associated with ${node.title} then email contact@osf.io with the subject line "Claiming Error" to report the problem.

Sincerely,

Open Science Framework Robot



Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science. Questions? Email contact@osf.io


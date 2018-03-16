<%!
    from website import settings
%>

Hello ${fullname},

You have been added by ${referrer.fullname} as a contributor to the project "${node.title}" on the Open Science Framework. To set a password for your account, visit:

${claim_url}

Once you have set a password, you will be able to make contributions to "${node.title}" and create your own projects. You will automatically be subscribed to notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}

To preview "${node.title}" click the following link: ${node.absolute_url}

(NOTE: if this project is private, you will not be able to view it until you have confirmed your account)

If you are not ${fullname} or you are erroneously being associated with "${node.title}" then email ${osf_contact_email} with the subject line "Claiming Error" to report the problem.


Sincerely,

Open Science Framework Robot


Center for Open Science

210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903-5083

Privacy Policy: https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md


Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.

Questions? Email ${osf_contact_email}

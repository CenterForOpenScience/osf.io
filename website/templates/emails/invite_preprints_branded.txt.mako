<%!
    from website import settings
%>

Hello ${fullname},

You have been added by ${referrer.fullname} as a contributor to the ${branded_service.preprint_word} "${node.title}" on ${branded_service.name}, powered by the Open Science Framework. To set a password for your account, visit:

${claim_url}

Once you have set a password, you will be able to make contributions to "${node.title}" and create your own ${branded_service.preprint_word}. You will automatically be subscribed to notification emails for this ${branded_service.preprint_word}. Each ${branded_service.preprint_word} is associated with a project on the Open Science Framework for managing the ${branded_service.preprint_word}.  To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}

To preview "${node.title}" click the following link: ${node.absolute_url}

(NOTE: if this project is private, you will not be able to view it until you have confirmed your account)

If you are not ${fullname} or you have been erroneously associated with "${node.title}", then email contact+${branded_service._id}@osf.io with the subject line "Claiming Error" to report the problem.


Sincerely,

Your ${branded_service.name} and OSF teams


Center for Open Science

210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903-5083

Privacy Policy: https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md


Want more information? Visit https://osf.io/preprints/${branded_service._id} to learn about ${branded_service.name} or https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science.

Questions? Email support+${branded_service._id}@osf.io

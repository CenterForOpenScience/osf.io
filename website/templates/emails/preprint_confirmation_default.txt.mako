<%!
    from website import settings
%>

Hello ${user.fullname},

Congratulations on sharing your preprint "${node.title}" on OSF Preprints: ${preprint.absolute_url}

Now that you've shared your preprint, take advantage of more OSF features:

*Upload supplemental, materials, data, and code to the OSF project associated with your preprint: ${node.absolute_url} Learn how: http://help.osf.io/m/preprints/l/685323-add-supplemental-files-to-a-preprint

*Preregister your next study and become eligible for a $1000 prize: osf.io/prereg

*Track your impact with preprint downloads



You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '} notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + 'settings/notifications/'}

Sincerely,

Your OSF Team

Want more information? Visit https://osf.io/ to learn about the Open Science Framework or https://cos.io/ for information about its supporting organization, the Center for Open Science.

Questions? Email ${osf_contact_email}



Center for Open Science

210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903-5083

Privacy Policy: https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md

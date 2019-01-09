<%!
    from website import settings
%>

Hello ${user.fullname},

Congratulations on sharing your ${preprint.provider.preprint_word} "${node.title}" on ${preprint.provider.name}, powered by GakuNin RDM Preprints: ${preprint.absolute_url}

Now that you've shared your ${preprint.provider.preprint_word}, take advantage of more GakuNin RDM features:

*Upload supplemental, materials, data, and code to the GakuNin RDM project associated with your ${preprint.provider.preprint_word}: ${node.absolute_url}
Learn how: http://help.osf.io/m/preprints/l/685323-add-supplemental-files-to-a-preprint

*Preregister your next study and become eligible for a $1000 prize: osf.io/prereg

*Track your impact with ${preprint.provider.preprint_word} downloads



You will ${'not receive ' if all_global_subscriptions_none else 'be automatically subscribed to '}notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}

Sincerely,

Your ${preprint.provider.name} and GakuNin RDM teams

Want more information? Visit ${preprint.provider.landing_url} to learn about ${preprint.provider.name} or https://rdm.nii.ac.jp/ to learn about the GakuNin RDM, or https://nii.ac.jp/ for information about its supporting organization, the National Institute of Informatics.

Questions? Email support+${preprint.provider._id}@osf.io



National Institute of Informatics

2-1-2 Hitotsubashi, Chiyoda Ward, Tokyo 101-8430, JAPAN

Privacy Policy: https://meatwiki.nii.ac.jp/confluence/pages/viewpage.action?pageId=32676422


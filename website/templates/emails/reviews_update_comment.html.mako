## -*- coding: utf-8 -*-
<div style="margin: 40px;">
    <p>Hello ${recipient.fullname},</p>
    <p>
        Your ${reviewable.provider.preprint_word} "${reviewable.node.title}" has an updated comment by the moderator.
        To view the comment, go to your <a href="${reviewable.absolute_url}">${reviewable.provider.preprint_word}</a>.
    </p>
    <p>
        You will ${'not receive ' if no_future_emails else 'be automatically subscribed to '}future notification emails
        for this ${reviewable.provider.preprint_word}. Each ${reviewable.provider.preprint_word} is associated with a
        project on the GakuNin RDM for managing the ${reviewable.provider.preprint_word}. To change your
        email notification preferences, visit your <a href="${'{}settings/notifications/'.format(domain)}">user settings</a>.
    </p>
    <p>
        If you have been erroneously associated with "${reviewable.node.title}", then you may visit the project's
        "Contributors" page and remove yourself as a contributor.
    </p>
    <p>
        For more information about ${reviewable.provider.name}, visit <a href="${provider_url}">${provider_url}</a> to
        learn more. To learn about the GakuNin RDM, visit <a href="https://rdm.nii.ac.jp/">https://rdm.nii.ac.jp/</a>.
    </p>
    <p>For questions regarding submission criteria, please email ${provider_contact_email}</p>
    <br>
    Sincerely,
    <br>
    Your ${reviewable.provider.name} and GakuNin RDM teams
    <p>
    National Institute of Informatics<br>
    210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903
    </p>
    <a href="https://meatwiki.nii.ac.jp/confluence/pages/viewpage.action?pageId=32676422">Privacy Policy</a>
</div>

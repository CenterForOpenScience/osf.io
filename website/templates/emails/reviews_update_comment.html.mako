## -*- coding: utf-8 -*-
<div style="margin: 40px;">
    <p>Hello ${recipient.fullname},</p>
    <p>
        Your ${reviewable.provider.preprint_word} "<a href="${reviewable.absolute_url}">${reviewable.title}</a>" has an updated comment by the moderator:<br/>
        ${comment}
    </p>
    <p>
        You will ${'not receive ' if no_future_emails else 'be automatically subscribed to '}future notification emails
        for this ${reviewable.provider.preprint_word}. Each ${reviewable.provider.preprint_word} is associated with a
        project on the Open Science Framework for managing the ${reviewable.provider.preprint_word}. To change your
        email notification preferences, visit your <a href="${'{}settings/notifications/'.format(domain)}">user settings</a>.
    </p>
    <p>
        If you have been erroneously associated with "${reviewable.title}", then you may visit the project's
        "Contributors" page and remove yourself as a contributor.
    </p>
    <p>
        For more information about ${reviewable.provider.name}, visit <a href="${provider_url}">${provider_url}</a> to
        learn more. To learn about the Open Science Framework, visit <a href="https://osf.io/">https://osf.io/</a>.
    </p>
    <p>For questions regarding submission criteria, please email ${provider_contact_email}</p>
    <br>
    Sincerely,
    <br>
    Your ${reviewable.provider.name} and OSF teams
</div>

## -*- coding: utf-8 -*-
<div style="margin: 40px;">
    Hello ${user.fullname},
    <br><br>
    Your ${reviewable.provider.preprint_word} "${reviewable.node.title}" has an updated comment by the moderator. To view the comment, go to your <a href="${reviewable.absolute_url}">${reviewable.provider.preprint_word}</a>.
    <br><br>
    You will ${'not receive ' if no_future_emails else 'be automatically subscribed to '}future notification emails for this ${reviewable.provider.preprint_word}. Each ${reviewable.provider.preprint_word} is associated with a project on the Open Science Framework for managing the ${reviewable.provider.preprint_word}. To change your email notification preferences, visit your <a href="${domain + 'settings/notifications/'}">project user settings</a>.
    <br><br>
    If you have been erroneously associated with "${reviewable.node.title}", then you may visit the project's "Contributors" page and remove yourself as a contributor.
    <br><br>
    For more information about ${reviewable.provider.name}, visit <a href="${provider_url}">${provider_url}</a> to learn more. To learn about the Open Science Framework, visit <a href="https://osf.io/">https://osf.io/</a>.
    <br><br>
    For questions regarding submission criteria, please email ${provider_contact_email}
    <br><br><br>
    Sincerely,
    <br>
    Your ${reviewable.provider.name} and OSF teams
    <br><br>
    Center for Open Science<br>
    210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903-5083
    <br><br>
    <a href="https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>
</div>

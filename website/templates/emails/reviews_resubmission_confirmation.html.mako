## -*- coding: utf-8 -*-
<div style="margin: 40px;">
    <p>Hello ${recipient.fullname},</p>
        <p>
            The ${reviewable.provider.preprint_word}
            <a href="${reviewable.absolute_url}">${reviewable.title}</a>
            has been successfully re-submitted to ${reviewable.provider.name}.
        </p>
        <p>
            ${reviewable.provider.name} has chosen to moderate their submissions using a
            pre-moderation workflow, which means your submission is pending until accepted
            by a moderator.
            % if not no_future_emails:
                You will receive a separate notification informing you of any status changes.
            % endif
        </p>
        <p>
            You will ${'not receive ' if no_future_emails else 'be automatically subscribed to '}future
            notification emails for this ${reviewable.provider.preprint_word}.
        </p>
        <p>
            If you have been erroneously associated with "${reviewable.title}", then you
            may visit the ${reviewable.provider.preprint_word}'s "Edit" page and remove yourself as a contributor.
        </p>
        <p>
            For more information about ${reviewable.provider.name}, visit
            <a href="${provider_url}">${provider_url}</a> to learn more. To learn about the
            Open Science Framework, visit <a href="https://osf.io/">https://osf.io/</a>.
        </p>
        <p>For questions regarding submission criteria, please email ${provider_contact_email}</p>
        <br>
        Sincerely,<br>
        Your ${reviewable.provider.name} and OSF teams
        <p>
            Center for Open Science<br>
            210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903
        </p>
        <a href="https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>
</div>

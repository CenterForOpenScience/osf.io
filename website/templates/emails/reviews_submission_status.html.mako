## -*- coding: utf-8 -*-
<div style="margin: 40px;">
    <p>Hello ${recipient.fullname},</p>
    <p>
        % if workflow == 'pre-moderation':
            Your submission "${reviewable.node.title}", submitted to ${reviewable.provider.name} has
            % if is_rejected:
                not been accepted. Admins may edit the ${reviewable.provider.preprint_word} and
                resubmit, at which time it will return to a pending state and be reviewed by a moderator.
            % else:
                been accepted by the moderator and is now discoverable to others.
            % endif
        % elif workflow == 'post-moderation':
            Your submission "${reviewable.node.title}", submitted to ${reviewable.provider.name} has
            % if is_rejected:
                not been accepted and will be made private and not discoverable by others.
                Admins may edit the ${reviewable.provider.preprint_word} and contact
                the moderator at ${provider_contact_email} to resubmit.
            % else:
                been accepted by the moderator and ${'remains' if was_pending else 'is now'} discoverable to others.
            % endif
        % endif

        % if notify_comment:
            The moderator has also provided a comment that is only visible to contributors
            of the ${reviewable.provider.preprint_word}, and not to others.
        % endif
    </p>
    <p>
        You will ${'not receive ' if no_future_emails else 'be automatically subscribed to '}future
        notification emails for this ${reviewable.provider.preprint_word}. Each
        ${reviewable.provider.preprint_word} is associated with a project on the
        Open Science Framework for managing the ${reviewable.provider.preprint_word}.
        To change your email notification preferences, visit your
        <a href="${'{}settings/notifications/'.format(domain)}">user settings</a>.
    </p>
    <p>
        If you have been erroneously associated with "${reviewable.node.title}", then you
        may visit the project's "Contributors" page and remove yourself as a contributor.
    </p>
    <p>
        For more information about ${reviewable.provider.name}, visit
        <a href="${provider_url}">${provider_url}</a>
        to learn more. To learn about the Open Science Framework, visit
        <a href="https://osf.io/">https://osf.io/</a>.
    </p>
    <p>
        For questions regarding submission criteria, please email ${provider_contact_email}
    </p>
    <br>
    Sincerely,<br>
    Your ${reviewable.provider.name} and OSF teams
    <p>
        Center for Open Science<br>
        210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903
    </p>
    <a href="https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>
</div>

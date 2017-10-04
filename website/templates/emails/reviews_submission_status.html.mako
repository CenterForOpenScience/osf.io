## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        Hello ${user.fullname},
        <br><br>
        % if workflow == 'pre-moderation':
        Your submission "${reviewable.node.title}", submitted to ${reviewable.provider.name} has ${'not been accepted. You may edit the '+ reviewable.provider.preprint_word+ ' and resubmit, at which time it will becoming pending moderation.' if is_rejected else 'been accepted by the moderator and is now discoverable to others.'}
        % elif workflow == 'post-moderation':
        Your submission "${reviewable.node.title}", submitted to ${reviewable.provider.name} has ${'not been accepted and will be made private and not discoverable by others. You may edit the '+ reviewable.provider.preprint_word+ ' and contact the moderator at '+ provider_support_email +' to resubmit.' if is_rejected else 'been accepted by the moderator and remains discoverable to others. '} ${'The moderator has also provided a comment that is only visible to contributors of the '+ reviewable.provider.preprint_word+ ', and not to others. ' if notify_comment else ''}
        % endif
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
</%def>

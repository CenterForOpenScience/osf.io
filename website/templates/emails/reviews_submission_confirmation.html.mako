## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        Hello ${user.fullname},
        <br><br>
        % if is_creator:
        Your ${reviewable.provider.preprint_word} <a href="${reviewable.absolute_url}">${reviewable.node.title}</a> has been successfully submitted to ${reviewable.provider.name}.
        % else:
        ${referrer.fullname} has added you as a contributor to the ${reviewable.provider.preprint_word} <a href="${reviewable.absolute_url}">${reviewable.node.title}</a> on ${reviewable.provider.name}, which is hosted on the Open Science Framework.
        % endif
        <br><br>
        % if workflow == 'pre-moderation':
        ${reviewable.provider.name} has chosen to moderate their submissions using a pre-moderation workflow, which means your submission is pending until accepted by a moderator. You will receive a separate notification informing you of any status changes.
        % elif workflow == 'post-moderation':
        ${reviewable.provider.name} has chosen to moderate their submissions using a post-moderation workflow, which means your submission is public and discoverable, while still pending acceptance by a moderator. You will receive a separate notification informing you of any status changes.
        % endif
        <br><br>
        You will ${'not receive ' if no_future_emails else 'be automatically subscribed to '}future notification emails for this ${reviewable.provider.preprint_word}. Each ${reviewable.provider.preprint_word} is associated with a project on the Open Science Framework for managing the ${reviewable.provider.preprint_word}. To change your email notification preferences, visit your <a href="${domain + 'settings/notifications/'}">project user settings</a>.
        <br><br>
        If you have been erroneously associated with "${reviewable.node.title}", then you may visit the project's "Contributors" page and remove yourself as a contributor.
        <br><br>
        For more information about ${reviewable.provider.name}, visit <a href="${provider_url}">${provider_url}</a> to learn more. To learn about the Open Science Framework, visit <a href="https://osf.io/">https://osf.io/</a>.
        <br><br>
        For questions regarding submission criteria, please email ${provider_contact_email}
        <br><br>
        <br>
        Sincerely,<br>
        Your ${reviewable.provider.name} and OSF teams
        <br><br>
        Center for Open Science<br>
        210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903-5083
        <br><br>
        <a href="https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>
    </div>
</%def>

## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <% from website import settings %>
    <div style="margin: 40px;">
        <p>Hello ${recipient.fullname},</p>
        <p>
            % if workflow == 'pre-moderation':
                Your submission "${reviewable.node.title}", submitted to ${reviewable.provider.name} has
                % if is_rejected:
                    not been accepted. Contributors with admin permissions may edit the ${reviewable.provider.preprint_word} and
                    resubmit, at which time it will return to a pending state and be reviewed by a moderator.
                % else:
                    been accepted by the moderator and is now discoverable to others.
                % endif
            % elif workflow == 'post-moderation':
                Your submission "${reviewable.node.title}", submitted to ${reviewable.provider.name} has
                % if is_rejected:
                    not been accepted and will be made private and not discoverable by others.
                    Contributors with admin permissions may edit the ${reviewable.provider.preprint_word} and contact
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
        % if not is_rejected:
            Now that you've shared your ${reviewable.provider.preprint_word}, take advantage of more OSF features:<br><br>
                * Upload supplemental, materials, data, and code to the OSF project associated with your ${reviewable.provider.preprint_word}: ${reviewable.node.absolute_url}.
                  Learn how: <a href="http://help.osf.io/m/preprints/l/685323-add-supplemental-files-to-a-preprint" target="_blank">help.osf.io</a><br><br>
                * Preregister your next study and become eligible for a $1000 prize: <a href="https://goo.gl/Wj5oBB">osf.io/prereg</a><br><br>
                * Or share on social media: Tell your friends through:
                    <a href="${'https://twitter.com/home?status=Read%20my%20{word}%2C%20%E2%80%9C{title}%E2%80%9D%20on%20{name}%20{link}'.format(word=reviewable.provider.preprint_word,title=reviewable.node.title, name=reviewable.provider.name, link=reviewable.absolute_url)}" target="_blank">
                        <img src="'{}static/img/fa-twitter-blue.png'.format(settings.DOMAIN)}" alt="twitter" width="20" style="padding-left: 5px; vertical-align: bottom;">
                    </a>
                    <a href="${'https://www.facebook.com/sharer/sharer.php?u={link}%3Futm_source%3Dnotification%26utm_medium%3Demail%26utm_campaign%3Dpreprint_review_status'.format(link=reviewable.absolute_url)}" target="_blank">
                        <img src="'{}static/img/fa-facebook-blue.png'.format(settings.DOMAIN)}" alt="facebook" style="padding-left: 5px; vertical-align: bottom;" width="20">
                    </a>
                    <a href="${'https://www.linkedin.com/shareArticle?mini=true&url={link}&summary=Read%20my%20{word}%2C%20%E2%80%9C{title}%E2%80%9D%20on%20{name}%20{link}&title=I%20just%20posted%20a%20{word}&source='.format(word=reviewable.provider.preprint_word,title=reviewable.node.title, name=reviewable.provider.name, link=reviewable.absolute_url)}" target="_blank">
                        <img src="${'{}static/img/fa-linkedin-blue.png'.format(settings.DOMAIN)}" alt="LinkedIn" style="padding-left: 5px; vertical-align: bottom;" width="20">
                    </a>
        % endif
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
    </div>
</%def>

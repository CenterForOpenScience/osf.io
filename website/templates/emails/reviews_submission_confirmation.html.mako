## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <% from website import settings %>
    <div style="margin: 40px;">
        <p>Hello ${user.fullname},</p>
        % if is_creator:
            <p>
                Your ${reviewable.provider.preprint_word}
                <a href="${reviewable.absolute_url}">${reviewable.node.title}</a>
                has been successfully submitted to ${reviewable.provider.name}.
            </p>
        % else:
            <p>
                ${referrer.fullname} has added you as a contributor to the
                ${reviewable.provider.preprint_word}
                <a href="${reviewable.absolute_url}">${reviewable.node.title}</a>
                on ${reviewable.provider.name}, which is hosted on the Open Science Framework.
            </p>
        % endif
        <p>
            % if workflow == 'pre-moderation':
                ${reviewable.provider.name} has chosen to moderate their submissions using a pre-moderation workflow,
                which means your submission is pending until accepted by a moderator.
            % elif workflow == 'post-moderation':
                ${reviewable.provider.name} has chosen to moderate their submissions using a
                post-moderation workflow, which means your submission is public and discoverable,
                while still pending acceptance by a moderator.
            % else:
                Now that you've shared your ${reviewable.provider.preprint_word}, take advantage of more OSF features:
                <ul>
                    <li>
                      Upload supplemental, materials, data, and code to the OSF project associated with your ${reviewable.provider.preprint_word}: ${reviewable.node.absolute_url}.<br>
                      Learn how: <a href="http://help.osf.io/m/preprints/l/685323-add-supplemental-files-to-a-preprint" target="_blank">help.osf.io</a>
                    </li>
                    <li>Preregister your next study and become eligible for a $1000 prize: <a href="https://goo.gl/Wj5oBB">osf.io/prereg</a></li>
                    <li>Or share on social media: Tell your friends through:<br>
                      <a href="${'https://twitter.com/home?status=Read%20my%20{word}%2C%20%E2%80%9C{title}%E2%80%9D%20on%20{name}%20{link}%3Futm_source%3Dnotification%26utm_medium%3Demail%26utm_campaign%3Dpreprint_submit'.format(word=reviewable.provider.preprint_word,title=reviewable.node.title, name=reviewable.provider.name, link=reviewable.absolute_url)}" target="_blank">
                          <img src="${settings.DOMAIN + 'static/img/fa-twitter-blue.png'}" alt="twitter" width="20" style="padding-left: 5px;" align="bottom">
                      </a>
                      <a href="${'https://www.facebook.com/sharer/sharer.php?u={link}%3Futm_source%3Dnotification%26utm_medium%3Demail%26utm_campaign%3Dpreprint_submit'.format(link=reviewable.absolute_url)}" target="_blank">
                          <img src="${settings.DOMAIN + 'static/img/fa-facebook-blue.png'}" alt="facebook" style="padding-left: 5px;" width="20">
                      </a>
                      <a href="${'https://www.linkedin.com/shareArticle?mini=true&url={link}%3Futm_source%3Dnotification%26utm_medium%3Demail%26utm_campaign%3Dpreprint_submit&summary=Read%20my%20{word}%2C%20%E2%80%9C{title}%E2%80%9D%20on%20{name}%20{link}&title=I%20just%20posted%20a%20{word}&source='.format(word=reviewable.provider.preprint_word,title=reviewable.node.title, name=reviewable.provider.name, link=reviewable.absolute_url)}" target="_blank">
                          <img src="${settings.DOMAIN + 'static/img/fa-linkedin-blue.png'}" alt="LinkedIn" style="padding-left: 5px;" width="20">
                      </a>
                    </li>
                </ul>
            % endif
            % if not no_future_emails:
                You will receive a separate notification informing you of any status changes.
            % endif
        </p>
        <p>
            You will ${'not receive ' if no_future_emails else 'be automatically subscribed to '}future
            notification emails for this ${reviewable.provider.preprint_word}.
            Each ${reviewable.provider.preprint_word} is associated with a project on the
            Open Science Framework for managing the ${reviewable.provider.preprint_word}. To change
            your email notification preferences, visit your
            <a href="${'{}settings/notifications/'.format(domain)}">user settings</a>.
        </p>
        <p>
            If you have been erroneously associated with "${reviewable.node.title}", then you may visit the project's
            "Contributors" page and remove yourself as a contributor.
        </p>
        <p>
            For more information about ${reviewable.provider.name}, visit
            <a href="${provider_url}">${provider_url}</a>
            to learn more. To learn about the Open Science Framework, visit
            <a href="https://osf.io/">https://osf.io/</a>.
        </p>
        <p>For questions regarding submission criteria, please email ${provider_contact_email}</p>
        <br>
        Sincerely,<br>
        Your ${reviewable.provider.name} and OSF teams
    </div>
</%def>

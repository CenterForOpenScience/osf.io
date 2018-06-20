## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <% from website import settings %>
    <%
        isOsfSubmission = reviewable.provider.name == 'Open Science Framework'
        if isOsfSubmission:
            reviewable.provider.name = 'OSF Preprints'
    %>
    <tr>
        <td>
            <div style="margin: 40px; background: white;">
                <p>Hello ${user.fullname},</p>
                % if is_creator:
                    <p>
                        Your ${reviewable.provider.preprint_word}
                        <a href="${reviewable.absolute_url}">${reviewable.title}</a>
                        has been successfully submitted to ${reviewable.provider.name}.
                    </p>
                % else:
                    <p>
                        ${referrer.fullname} has added you as a contributor to the
                        ${reviewable.provider.preprint_word}
                        <a href="${reviewable.absolute_url}">${reviewable.title}</a>
                        on ${reviewable.provider.name}, which is hosted on the OSF.
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
                        <table style="padding: 0; border: 0;" width="100%" border="0" cellspacing="0" cellpadding="0" align="center">
                            <tbody>
                                <tr>
                                    <td>
                                    Now that you've shared your ${reviewable.provider.preprint_word}, take advantage of more OSF features:
                                        <ul>
                                            <li>Upload supplemental, materials, data, and code to an OSF project associated with your ${reviewable.provider.preprint_word}.
                                                <a href="http://help.osf.io/m/preprints/l/685323-add-supplemental-files-to-a-preprint" target="_blank">Learn how</a></li>
                                            <li>Preregister your next study. <a href="http://help.osf.io/m/registrations/l/524205-register-your-project">Read more</a></li>
                                            <li>Or share on social media: Tell your friends through:
                                                <table style="display: inline-table;" width="53" border="0" cellspacing="0" cellpadding="0" align="center">
                                                    <tbody>
                                                        <tr>
                                                            <td>
                                                                <a href="${u'https://twitter.com/home?status=Read%20my%20{word}%2C%20%E2%80%9C{title}%E2%80%9D%20on%20{name}%20{link}'.format(word=reviewable.provider.preprint_word,title=reviewable.title, name=reviewable.provider.name, link=reviewable.absolute_url)}" target="_blank">
                                                                    <img src="${'{}static/img/fa-twitter-blue.png'.format(settings.DOMAIN)}" alt="twitter" style="display: block; border: 0;outline: none;text-decoration: none; text-align: center;vertical-align: bottom;" width="14">
                                                                </a>
                                                            </td>
                                                            <td>
                                                                <a href="${u'https://www.facebook.com/sharer/sharer.php?u={link}%3Futm_source%3Dnotification%26utm_medium%3Demail%26utm_campaign%3Dpreprint_submit'.format(link=reviewable.absolute_url)}" target="_blank">
                                                                    <img src="${'{}static/img/fa-facebook-blue.png'.format(settings.DOMAIN)}" alt="facebook" style="display: block; border: 0;outline: none;text-decoration: none; text-align: center;vertical-align: bottom;" width="14">
                                                                </a>
                                                            </td>
                                                            <td>
                                                                <a href="${u'https://www.linkedin.com/shareArticle?mini=true&url={link}&summary=Read%20my%20{word}%2C%20%E2%80%9C{title}%E2%80%9D%20on%20{name}%20{link}&title=I%20just%20posted%20a%20{word}&source='.format(word=reviewable.provider.preprint_word,title=reviewable.title, name=reviewable.provider.name, link=reviewable.absolute_url)}" target="_blank">
                                                                    <img src="${'{}static/img/fa-linkedin-blue.png'.format(settings.DOMAIN)}" alt="LinkedIn" style="display: block; border: 0;outline: none;text-decoration: none; text-align: center;vertical-align: bottom;" width="14">
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </li>
                                        </ul>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    % endif
                    % if not no_future_emails and not isOsfSubmission:
                        You will receive a separate notification informing you of any status changes.
                    % endif
                </p>
                % if not is_creator:
                <p>
                    If you have been erroneously associated with "${reviewable.title}," then you may visit the ${reviewable.provider.preprint_word}
                    and remove yourself as a contributor.
                </p>
                % endif
                <p>Learn more about <a href="${provider_url}">${reviewable.provider.name}</a> or <a href="https://osf.io/">OSF</a>.</p>
                <br>
                <p>
                    Sincerely,<br>
                    ${'Your OSF team' if isOsfSubmission else 'Your {provider} and OSF teams'.format(provider=reviewable.provider.name)}
                </p>
            </div>
        </td>
    </tr>
</%def>

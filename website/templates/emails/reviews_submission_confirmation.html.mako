## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <% from website import settings %>
    <%
        isOsfSubmission = reviewable_provider_name == 'Open Science Framework'
    %>
    <tr>
        <td>
            % if document_type == 'registration':
                <div style="margin: 40px; background: white;">
                    Hello ${user_fullname},
                    <p>
                    Your ${document_type} <a href="${reviewable_absolute_url}">${reviewable_title}</a> has been successfully submitted to ${reviewable_provider_name}.
                    <p>
                    ${reviewable_provider_name} has chosen to moderate their submissions using a pre-moderation workflow, which means your submission is pending until accepted by a moderator.
                    <p>
                    You will receive a separate notification informing you of any status changes.
                    <p>
                    Learn more about <a href="${provider_url}">${reviewable_provider_name}</a> or <a href="https://osf.io/">OSF</a>.
                    <p>
                    Sincerely,
                    The ${reviewable_provider_name} and OSF teams.
                </div>
            % else:
                <div style="margin: 40px; background: white;">
                    <p>Hello ${user_fullname},</p>
                    % if is_creator:
                        <p>
                            Your ${document_type}
                            <a href="${reviewable_absolute_url}">${reviewable_title}</a>
                            has been successfully submitted to ${reviewable_provider_name}.
                        </p>
                    % else:
                        <p>
                            ${referrer_fullname} has added you as a contributor to the
                            ${document_type}
                            <a href="${reviewable_absolute_url}">${reviewable_title}</a>
                            on ${reviewable_provider_name}, which is hosted on the OSF.
                        </p>
                    % endif
                    <p>
                        % if workflow == 'pre-moderation':
                            ${reviewable_provider_name} has chosen to moderate their submissions using a pre-moderation workflow,
                            which means your submission is pending until accepted by a moderator.
                        % elif workflow == 'post-moderation':
                            ${reviewable_provider_name} has chosen to moderate their submissions using a
                            post-moderation workflow, which means your submission is public and discoverable,
                            while still pending acceptance by a moderator.
                        % else:
                        <table style="padding: 0; border: 0;" width="100%" border="0" cellspacing="0" cellpadding="0" align="center">
                            <tbody>
                                <tr>
                                    <td>
                                        Now that you've shared your ${document_type}, take advantage of more OSF features:
                                        <ul>
                                            <li>Upload supplemental materials, data, and code to an OSF project associated with your ${document_type}.
                                                <a href="https://help.osf.io/article/177-upload-a-preprint" target="_blank">Learn how</a></li>
                                            <li>Preregister your next study. <a href="https://help.osf.io/article/145-preregistration">Read more</a></li>
                                            <li>Or share on social media: Tell your friends through:
                                                <table style="display: inline-table;" width="53" border="0" cellspacing="0" cellpadding="0" align="center">
                                                    <tbody>
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
                        If you have been erroneously associated with "${reviewable_title}," then you may visit the ${document_type}
                        and remove yourself as a contributor.
                    </p>
                    % endif
                    <p>Learn more about <a href="${provider_url}">${reviewable_provider_name}</a> or <a href="https://osf.io/">OSF</a>.</p>
                    <br>
                    <p>
                        Sincerely,<br>
                        The OSF team
                    </p>
                </div>
            % endif
        </td>
    </tr>
</%def>

## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako" />

<% from website import util %>
<%def name="build_message(d)">
    <table class="block" width="100%" border="0" cellpadding="15" cellspacing="0" align="center">
        <thead class="block-head">
            % if provider_type == 'preprint':
                <tr>
                    <th colspan="2" style="padding: 0px 15px 0 15px">
                        <h3 style="padding: 0 15px 5px 15px; margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300; border-bottom: 1px solid #eee; text-align: left;">
                            Visit your <a href=${reviews_submissions_url}>provider’s submissions</a>
                        </h3>
                    </th>
                </tr>
            % else:
                <tr>
                    <th colspan="2" style="padding: 0px 15px 0 15px">
                        <h3 style="padding: 0 15px 5px 15px; margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300; border-bottom: 1px solid #eee; text-align: left;">
                            Hello ${user.fullname},
                            <br>
                            Below are the recent registration submission and withdrawal requests that require attention.
                            <br>
                            Visit your <a href=${reviews_submissions_url}> provider's submissions.</a>
                            <br>
                            Visit your <a href=${reviews_withdrawal_url}> provider's withdrawal requests.</a>
                        </h3>
                    </th>
                </tr>
            % endif
        </thead>
        <tbody>
            <tr>
                <td style="border-collapse: collapse;">
                    %for item in d:
                        ${item['message']}
                    %endfor
                </td>
            </tr>
        </tbody>
    </table>
    % if provider_type == 'registration':
        You are receiving these emails because you are a moderator on {provider.name}. To change your moderation notification preferences, visit your <a href="https://osf.io/settings/notifications/"> notification settings.</a>
    % endif
</%def>

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Recent Submissions to ${provider_name}</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    ${build_message(message)}
  </td>
</tr>
</%def>

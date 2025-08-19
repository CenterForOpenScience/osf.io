<!doctype html>
<html class="no-js" lang="">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <meta name="description" content="Center for Open Science Notifications">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>

<%page args="
    provider_name='OSF',
    logo='osf',
    logo_url=None,
    OSF_LOGO_LIST=(),
    can_change_preferences=True,
    can_change_node_preferences=False,
    is_reviews_moderator_notification=False,
    referrer=False,
    is_admin=False,
    domain='',
    node__id=None,
    node_absolute_url=None,
    notification_settings_url=None,
    osf_contact_email='support@osf.io',
    year=2025
"/>

<body leftmargin="0" marginwidth="0" topmargin="0" marginheight="0" offset="0"
      style="-webkit-text-size-adjust: none;font-family: Helvetica, Arial, sans-serif;background: #eeeeee;padding: 0;margin: 0;border: none;list-style: none;width: 100% !important;">
    <table id="layout-table" width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr>
            <td style="border-collapse: collapse;">
                <table width="100%" border="0" cellpadding="10" cellspacing="0" height="100%">
                    <tbody>
                        <tr class="banner" style="background: #214762;color: white;">
                            <td class="text-center" style="border-collapse: collapse;text-align: center;">
                                <table id="header-logo" border="0" cellpadding="0" cellspacing="0" style="margin: 0 auto;padding: 0;">
                                    <tr>
                                        <td style="border-collapse: collapse;padding: 12px 0;">
                                            % if logo_url:
                                                <img src="${logo_url}" alt="${provider_name} logo"
                                                     style="border:0;height:auto;line-height:100%;outline:none;text-decoration:none;max-height:100px;">
                                            % elif OSF_LOGO_LIST and logo not in OSF_LOGO_LIST:
                                                <img src="https://raw.githubusercontent.com/CenterForOpenScience/osf-assets/master/files/preprints-assets/${logo}/wide_white.png"
                                                     alt="${provider_name} logo"
                                                     style="border:0;height:auto;line-height:100%;outline:none;text-decoration:none;max-height:100px;">
                                            % else:
                                                <img src="https://osf.io/static/img/${logo}.png"
                                                     alt="${provider_name} logo"
                                                     style="border:0;height:auto;line-height:100%;outline:none;text-decoration:none;max-height:100px;">
                                            % endif
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </td>
        </tr>

        <tr>
          <td style="border-collapse: collapse;">
            <table id="content" width="600" border="0" cellpadding="25" cellspacing="0" align="center"
                   style="margin: 30px auto 0 auto;background: #ffffff;box-shadow: 0 0 2px #ccc;">
              <tbody>
                ${self.content()}
              </tbody>
            </table>

            % if can_change_preferences:
            <table width="600" border="0" cellpadding="25" cellspacing="0" align="center"
                   style="margin: 30px auto 0 auto;background: #ffffff;box-shadow: 0 0 2px #ccc;">
                <tbody>
                    <tr>
                        <td style="border-collapse: collapse;">
                            % if is_reviews_moderator_notification:
                                <p class="text-smaller text-center" style="text-align: center;font-size: 12px;margin: 0;">
                                  % if not referrer:
                                        You are receiving these emails because you are ${'an administrator' if is_admin else 'a moderator'} on ${provider_name}.
                                  % endif
                                  <%
                                      ns_url = notification_settings_url or (domain + 'settings/notifications/')
                                  %>
                                  To change your moderation notification preferences,
                                  visit your <a href="${ns_url}">notification settings</a>.
                                </p>
                            % else:
                                <%
                                    ns_url = notification_settings_url or (domain + 'settings/notifications/')
                                    node_url = node_absolute_url or ((domain + node__id) if (domain and node__id) else None)
                                %>
                                <p class="text-smaller text-center" style="text-align: center;font-size: 12px;margin: 0;">
                                    To change how often you receive emails, visit
                                    % if can_change_node_preferences and node_url:
                                        this <a href="${node_url + '/settings#configureNotificationsAnchor'}">project's settings</a> for emails about this project or
                                    % endif
                                    your <a href="${ns_url}">user settings</a> to manage default email settings.
                                </p>
                            % endif
                        </td>
                    </tr>
                </tbody>
            </table>
            % endif
          </td>
        </tr>

        <tr>
            <td style="border-collapse: collapse; padding-top: 15px;">
                <table width="80%" border="0" cellpadding="10" cellspacing="0" align="center" class="footer"
                       style="margin-top: 45px;padding: 25px 0 35px;background-color: #f4f4f4;border-top: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;width: 100%;color: #555;">
                    <tbody>
                        <tr>
                            <td style="border-collapse: collapse;">
                                <p class="text-smaller text-center" style="text-align: center;font-size: 12px;margin: 0 0 6px 0;">
                                    Copyright &copy; 2025
                                    Center For Open Science, All rights reserved. |
                                    <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>
                                </p>
                                <p class="text-smaller text-center" style="text-align: center;font-size: 12px;margin: 0 0 6px 0;">
                                    210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903-5083
                                </p>
                                <p class="text-smaller text-center" style="text-align: center;font-size: 12px;margin: 0;">
                                    ${self.footer()}
                                </p>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>

<%def name="content()">
    <!-- Child templates override this block -->
</%def>

<%def name="footer()">
    Questions? Email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a>
</%def>

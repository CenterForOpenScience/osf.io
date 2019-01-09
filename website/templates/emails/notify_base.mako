<%!
    from website import settings
%>
<!doctype html>
<html class="no-js" lang="">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <meta name="description" content="National Institute of Informatics Notifications">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body leftmargin="0" marginwidth="0" topmargin="0" marginheight="0" offset="0" style="-webkit-text-size-adjust: none;font-family: 'Helvetica', sans-serif;background: #eeeeee;padding: 0;margin: 0;border: none;list-style: none;width: 100% !important;">
    <table id="layout-table" width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr>
            <td style="border-collapse: collapse;">
                <table id="layout-table" width="100%" border="0" cellpadding="10" cellspacing="0" height="100%">
                    <tbody>
                        <tr class="banner" style="background: #214762;color: white;">
                            <td class="text-center" style="border-collapse: collapse;text-align: center;">
                                <table id="header-logo" border="0" style="margin: 0 auto;padding: 0px;">
                                    <tr>
                                        <td style="border-collapse: collapse;">
                                            <img src="https://osf.io/static/img/cos-white2.png" alt="NII logo" width="36" style="border: 0;height: auto;line-height: 100%;outline: none;text-decoration: none;">
                                        </td>
                                        <td style="border-collapse: collapse;">
                                            <h2 style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;font-size: 20px;text-align: left; color:white;">GakuNin RDM</h2>
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
            <table id="content" width="600" border="0" cellpadding="25" cellspacing="0" align="center" style="margin: 30px auto 0 auto;background: white;box-shadow: 0 0 2px #ccc;">
              <tbody>
                ${self.content()}
              </tbody>
            </table>
            % if context.get('can_change_preferences', True):
            <table width="600" border="0" cellpadding="25" cellspacing="0" align="center" style="margin: 30px auto 0 auto;background: white;box-shadow: 0 0 2px #ccc;">
                <tbody>
                    <tr>
                        <td style="border-collapse: collapse;">
                            <p class="text-smaller text-center" style="text-align: center;font-size: 12px;">To change your email notification preferences, visit your project or <a href="${settings.DOMAIN + "settings/notifications/"}">user settings</a>. </p>
                        </td>
                    </tr>
                </tbody>
            </table>
            % endif
          </td>
        </tr>
        <tr>
            <td style="border-collapse: collapse; padding-top: 15px;">
                <table width="80%" border="0" cellpadding="10" cellspacing="0" align="center" class="footer" style="margin-top: 45px;padding: 25px 0 35px;background-color: rgb(244, 244, 244);border-top: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;width: 100%;color: #555;">
                    <tbody>
                        <tr>
                            <td style="border-collapse: collapse;">
                                <p class="text-smaller text-center" style="text-align: center;font-size: 12px;">Copyright &copy; 2017 Center For Open Science, All rights reserved. |
                                    <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>
                                </p>
                                <p class="text-smaller text-center" style="text-align: center;font-size: 12px;">2-1-2 Hitotsubashi, Chiyoda Ward, Tokyo 101-8430, JAPAN</p>
                                <p class="text-smaller text-center" style="text-align: center;font-size: 12px;">${self.footer()}</p>
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

</%def>

<%def name="footer()">

</%def>

<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>

<%page args="
    domain='',
    notification_settings_url=None,
    osf_contact_email='support@osf.io'
"/>

<body style="-webkit-text-size-adjust:none;font-family:Helvetica,Arial,sans-serif;background:#eeeeee;padding:0;margin:0;width:100%!important;">
<table width="100%" cellpadding="0" cellspacing="0">

    <tr>
        <td style="background:#214762;text-align:center;padding:22px 0;">
            <img
                src="${domain}static/img/osf.png"
                alt="OSF"
                style="max-height:100px;border:0;">
        </td>
    </tr>

    <tr>
        <td>
            <table width="600" cellpadding="25" cellspacing="0" align="center"
                   style="margin:30px auto 0;background:#fff;box-shadow:0 0 2px #ccc;">
                <tbody>
                    <!-- Email content goes here -->
                </tbody>
            </table>
        </td>
    </tr>

    <tr>
        <td style="padding-top:15px;">
            <table width="100%" cellpadding="10" cellspacing="0"
                   style="margin-top:45px;padding:25px 0 35px;background:#f4f4f4;border-top:1px solid #E5E5E5;border-bottom:1px solid #E5E5E5;color:#555;">
                <tr>
                    <td>
                        <p style="text-align:center;font-size:12px;margin:0 0 6px;">
                            Copyright &copy; 2025
                            Center For Open Science, All rights reserved. |
                            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">
                                Privacy Policy
                            </a>
                        </p>
                        <p style="text-align:center;font-size:12px;margin:0;">
                            Questions?
                            <a href="mailto:${osf_contact_email}">${osf_contact_email}</a>
                        </p>
                    </td>
                </tr>
            </table>
        </td>
    </tr>

</table>
</body>
</html>
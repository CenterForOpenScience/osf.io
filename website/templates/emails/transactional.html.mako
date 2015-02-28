<% from website.models import Node %>
<!doctype html>
<html class="no-js" lang="">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>COS Email Notification Template</title>
    <meta name="description" content="Center for Open Science Notifications">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* Client-specific Styles */
        #outlook a{padding:0;} /* Force Outlook to provide a "view in browser" button. */
        body{width:100% !important;} .ReadMsgBody{width:100%;} .ExternalClass{width:100%;} /* Force Hotmail to display emails at full width */
        body{-webkit-text-size-adjust:none;} /* Prevent Webkit platforms from changing default text sizes. */

        /* Reset Styles */
        img{border:0; height:auto; line-height:100%; outline:none; text-decoration:none;}
        table td{border-collapse:collapse;}
        #backgroundTable{height:100% !important; margin:0; padding:0; width:100% !important;}
        body, ul, h1, h2, h3, h4, h5, a, button, div {
            padding: 0;
            margin: 0;
            border: none;
            list-style: none;
        }
        h3 {
            margin: 30px 0 0 0;
        }
        body {
            font-family: 'Helvetica', sans-serif;
            background: #eeeeee ;
        }
        .text-center {
            text-align: center;
        }
        #header-logo {
            margin: 0 auto;
            padding: 0px
        }
        #header-logo h2 {
            font-weight: 300;
            font-size: 20px;
            text-align: left;
        }
        .div-center {
            margin: 0 auto;
        }
        a {
            color: #008de5;
            text-decoration: none;
        }
        .comment-block h3 {
            text-transform: uppercase;
            font-size: 16px;
            color: #214762;
            padding: 20px 0 10px 0;
            font-weight: 400;
        }
        h1, h2, h3, h4 {
            font-weight: 300;
        }
        .block-head th {
            border-bottom: 1px solid #eee;
            text-align: left;
            padding: 5px 15px;
        }
        small {
            font-size: 14px;
            color: #999;
        }
        .line {
            height: 4px;
            border-bottom: 1px solid #ddd;
            width: 80%;
            margin: 15px auto;
        }
        .comment-row {
            font-size: 13px;
            background: #fff;
            padding: 0px !important;
            border: 1px solid #eee;
            border-radius: 5px;
            margin-bottom: 10px;

        }
        .icon {
            font-size: 24px;
            color: #999;
        }
        .person {
            font-weight: bold;
        }
        .text{

        }
        .project {
            font-weight: bold;
        }
        .timestamp {
            color: grey;
        }
        .content {
            display: block;
            padding: 6px 5px 0px 8px;
            font-size: 14px;
        }
        p.small {
            font-size: 12px;
        }
        p.medium {
            font-size: 14px;
        }
        .indent {
            padding-left: 20px;
        }
        .btn {
            padding: 8px;
            font-size: 14px;
            border-radius: 3px;
            text-align: center;
            color: white;
            display: inline-block;
            margin: 3px;
        }
        .btn-primary {
            background: #337AB7;
        }
        .btn-success {
            background: #5CB85C;
        }
        .btn-info {
            background: #5BC0DE;
        }
        .btn-warning {
            background: #F0AD4E;
        }
        .btn-danger {
            background: #D9534F;
        }
        .banner {
            background:#214762;
            color: white;
        }
        #content {
            margin: 30px auto 0 auto;
            background: white;
            box-shadow: 0 0 2px #ccc;
        }
        .footer {
            margin-top: 45px;
            padding: 25px 0 35px;
            background-color: rgb(244, 244, 244);
            border-top: 1px solid #E5E5E5;
            border-bottom: 1px solid #E5E5E5;
            width: 100%;
            color: #555
        }
        .link {
            font-size: 18px;
            border-left: 1px solid #ddd;
        }
        .link a {
        }
        .avatar {
            border-radius: 25px;
        }

    </style>
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
                                    <img src="https://osf.io/static/img/cos-white2.png" alt="COS logo" width="36" style="border: 0;height: auto;line-height: 100%;outline: none;text-decoration: none;">
                                </td>
                                <td style="border-collapse: collapse;">
                                    <h2 style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;font-size: 20px;text-align: left;">Open Science Framework</h2>
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
                <tr>
                    <td style="border-collapse: collapse;">
                        <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Hello ${name}, there has been recent activity on your OSF projects! </h3>
                    </td>
                </tr>
                <tr>
                    <td style="border-collapse: collapse;">
                        <table class="block" width="100%" border="0" cellpadding="15" cellspacing="0" align="center" >
                            <thead class="block-head">
                            <th colspan="2">
                            <h3>
                                ${node_title}
                                %if Node.load(node_id).parent_node:
                                    <small> in ${Node.load(node_id).parent_node.title} </small>
                                %endif
                            </h3>
                            </th>
                            </thead>
                            <tbody>
                            <tr>
                                <td >
                                    ${message}                          
                                </td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                </tbody>
            </table>
        </td>
    </tr>
    <tr>
        <td style="border-collapse: collapse;">
            <table width="80%" border="0" cellpadding="10" cellspacing="0" align="center" class="footer" style="margin-top: 45px;padding: 25px 0 35px;background-color: rgb(244, 244, 244);border-top: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;width: 100%;color: #555;">
                <tbody>
                <tr>
                    <td style="border-collapse: collapse;">
                        <p class="small text-center" style="text-align: center;font-size: 12px;">Copyright &copy; 2015 Center For Open Science, All rights reserved. </p>
                        <p class="small text-center" style="text-align: center;font-size: 12px; line-height: 20px;">You received this email because you were subscribed to email notifications. <br /><a href="${url}" style="padding: 0;margin: 0;border: none;list-style: none;color: #008de5;text-decoration: none; font-weight: bold;">Update Subscription Preferences</a></p>
                    </td>
                </tr>
                </tbody>
            </table>
        </td>
    </tr>
</table>
</body>
</html>

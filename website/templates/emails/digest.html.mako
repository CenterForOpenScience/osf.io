<% from website.models import Node %>
<%def name="build_message(d, parent=None)">
%for key in d['children']:
    %if d['children'][key]['messages']:
        <h3> 
            ${Node.load(key).title}  
            %if parent :
                <small> in ${Noad.load(parent).title} </small>
            %endif 
        </h3> 
        %for m in d['children'][key]['messages']:
            ${m['message']}
        %endfor
    %endif
    %if isinstance(d['children'][key]['children'], dict):
        ${build_message(d['children'][key], key )}
    %endif
%endfor
</%def>

<!doctype html>
<html class="no-js" lang="">
    <head>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <title>COS Email Notification Template</title>
        <meta name="description" content="Center for Open Science Notifications">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href='http://fonts.googleapis.com/css?family=Open+Sans:400,600,300' rel='stylesheet' type='text/css'>
        <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css">
        <style>
            /* Client-specific Styles */
			#outlook a{padding:0;} /* Force Outlook to provide a "view in browser" button. */
			body{width:100% !important;} .ReadMsgBody{width:100%;} .ExternalClass{width:100%;} /* Force Hotmail to display emails at full width */
			body{-webkit-text-size-adjust:none;} /* Prevent Webkit platforms from changing default text sizes. */

			/* Reset Styles */
			img{border:0; height:auto; line-height:100%; outline:none; text-decoration:none;}
			table td{border-collapse:collapse;}
			#backgroundTable{height:100% !important; margin:0; padding:0; width:100% !important;}
            body, ul, h1, h2, h3, h4, h5, a, button {
                padding: 0;
                margin: 0;
                border: none;
                list-style: none;
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

            .comment-block h3 {
                text-transform: uppercase;
                font-size: 16px;
                color: #214762;
                padding: 20px 0 10px 0;
                font-weight: 400;
            }
            .line {
                height: 4px;
                border-bottom: 1px solid #ddd;
                width: 80%;
                margin: 20px auto;
            }
            .comment-row {
                font-size: 13px;
                box-shadow: 0 0 3px #ccc;
                background: white;
                padding: 5px !important; 
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
                padding: 5px;
                font-size: 14px;
            }
            p.small {
                font-size: 12px;
            }
        </style>
    </head>
       <body leftmargin="0" marginwidth="0" topmargin="0" marginheight="0" offset="0">
           <table id="layout-table" width="100%">
                <tr>
                    <td>
                        <table id="header" width="100%" border="0" cellpadding="0" cellspacing="0" height="100%"  id="layout-table">
                            <tr style="background:rgba(255, 255, 255, 0.73)">
                                <td class="text-center">
                                    <table id="header-logo" border="0" >
                                        <tr>
                                            <td>
                                                <img src="http://centerforopenscience.org/static/img/cos_center_logo_small.png" alt="COS logo" width="36" />
                                            </td>
                                            <td>
                                                <h2>Open Science Framework</h2>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td>
                       <table id="content" width="90%" border="0" cellpadding="0" cellspacing="0" align="center">
                           <tr> 
                            <td> 
                               <p class="lead text-center"> Hello ${name}, here's a summary of your notifications: </p>
                                <div class="comment-block div-center">
                                    ${build_message(message)}                               
                                </div>  
                               </td>
                           </tr> 
                        </table>
                   </td>
                </tr>
                <tr>
                    <td>
                        <table width="80%" border="0" cellpadding="10" cellspacing="0" align="center">
                            <tr>
                                <td>
                                    <div class="line"></div>
                                    <p class="small text-center">Copyright &copy; 2015 Center For Open Science, All rights reserved. </p>
                                    <p class="small text-center"><a href="#">View this email in a browser </a> |  <a href="#">update subscription preferences</a></p> 
                                </td>
                            </tr>
                        </table>
                   </td>
                </tr>
           </table>
        </body>
    </html>
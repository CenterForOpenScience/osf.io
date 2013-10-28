<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>${self.title()}</title>
    ## Can't use external css files in emails, so insert the minified bootstrap
    <%include file="bootstrap_email.mako"/>
</head>
<body>
    <table cellspacing="0" cellpadding="0" border="0" width="100%">
        <tr>
            <td class="navbar navbar-inverse" align="center">
                <!-- This setup makes the nav background stretch the whole width of the screen. -->
                <table width="650px" cellspacing="0" cellpadding="3" class="container">
                    <tr class="navbar navbar-inverse">
                        <td colspan="4"><a class="brand" href="http://openscienceframework.org">Open Science Framework</a></td>
                    </tr><!-- end navbar -->
                </table>
            </td>
        </tr>
        <tr>
            <td bgcolor="#FFFFFF" align="center">
                <table width="650px" cellspacing="0" cellpadding="3" class="container">
                    <tr>
                        <td>${self.content()}</td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td bgcolor="#FFFFFF" align="center">
                <table width="650px" cellspacing="0" cellpadding="3" class="container">
                    <tr>
                        <td>
                            <hr>
                            <p>Copyright &copy; 2011 <a href="http://centerforopenscience.org/">CenterForOpenscience.org</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>

###### Base email template interface ######

<%def name="title()">
    ### The html title ###
</%def>

<%def name="content()">
    ### The body content ###
</%def>

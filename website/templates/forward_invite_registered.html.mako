<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${referrer_fullname},<br>
    <br>
    You recently added ${user_fullname} to "${node_title}". ${user_fullname} wants to claim their account, but the email address they provided is different from the one you provided.  To maintain security of your project, we are sending the account confirmation to you first.<br>
    <br>
    IMPORTANT: To ensure that the correct person is added to your project please forward the message below to ${user_fullname}.<br>
    <br>
    After ${user_fullname} confirms their account, they will be able to contribute to the project.<br>
    <br>
    <br>
    ----------------------<br>
    <br>
    <br>
    Hello ${user_fullname},<br>
    <br>
    You have been added by ${referrer_fullname} as a contributor to the project "${node_title}" on the Open Science Framework. To claim yourself as a contributor to the project, visit this url:<br>
    <br>
    ${claim_url}<br>
    <br>
    Once you are logged in, you will be able to make contributions to ${node_title}.<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>
    <br>
    Want more information? Visit https://osf.io/ or https://cos.io/ for information about the Open Science Framework and its supporting organization, the Center for Open Science. Questions? Email ${osf_contact_email}<br>


</tr>
</%def>

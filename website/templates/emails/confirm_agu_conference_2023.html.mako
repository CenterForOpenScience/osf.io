<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>

    Thank you for joining us at the AGU Open Science Pavilion, and welcome to the Open Science Framework.

    We are pleased to offer a special AGU attendees exclusive community call to continue our conversation and to help
    you get oriented on the OSF. This is an opportunity for us to show you useful OSF features, talk about
    open science in your domains, and for you to ask any questions you may have.
    You can register for this free event here:
    <br>
    https://cos-io.zoom.us/meeting/register/tZAuceCvrjotHNG3n6XzLFDv1Rnn2hkjczHr
    <br><br>
    To confirm your OSF account, please verify your email address by visiting this link:<br>
    <br>
    ${confirmation_url}<br>
    <br>
    From the team at the Center for Open Science<br>

</tr>
</%def>

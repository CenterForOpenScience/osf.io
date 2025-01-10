<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>

    Thank you for joining us at the AGU Open Science Pavilion, and welcome to the Open Science Framework (OSF).

    We are pleased to offer a special AGU attendees exclusive 1:1 consultation to continue our conversation and to help
    you get oriented on the OSF. This is an opportunity for us to show you useful OSF features, talk about
    open science in Earth and space sciences, and for you to ask any questions you may have.
    You can sign up to participate by completing this form, and a member of our team will be in touch to
    determine your availability:
    <br>
    https://docs.google.com/forms/d/e/1FAIpQLSeJ23YPaEMdbLY1OqbcP85Tt6rhLpFoOtH0Yg4vY_wSKULRcw/viewform?usp=sf_link
    <br><br>
    To confirm your OSF account, please verify your email address by visiting this link:<br>
    <br>
    ${confirmation_url}<br>
    <br>
    From the team at the Center for Open Science<br>

</tr>
</%def>

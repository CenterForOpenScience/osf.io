## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako" />
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        Hello ${user_fullname},
        <br><br>
        We’ve noticed it’s been a while since you used the OSF. We have recently updated our User Interface with a new look for the User Profile page, <a href="https://help.osf.io/article/390-profile-and-account#Edit-Your-Profile-ZuHIE">go update your profile now</a>.
        Starting a new Research Project? Create a Research plan by <a href="https://help.osf.io/article/330-welcome-to-registrations#Create-a-Registration-_4D6l">submitting a Registration or Pre-registration</a>:
        <br>
        <ul>
            <li>If you plan on submitting your work for peer-review, make sure you <a href="https://help.osf.io/article/330-welcome-to-registrations#Privacy-Settings-t-8n2">embargo your Registration</a>.</li>
            <li>Come back and add research outputs to an existing Registration using <a href="https://help.osf.io/article/330-welcome-to-registrations#Add-Resources-to-your-Registration-wvpiz">Open Practice Badges</a>.</li>
        </ul>
        To get started now, visit your “My Registrations” page and click on “Add a Registration”
        Need help getting started? Check out the <a href="https://help.osf.io/article/353-welcome-to-projects">OSF Help Guides</a> or one of our recent <a href="https://www.youtube.com/channel/UCGPlVf8FsQ23BehDLFrQa-g">OSF 101 webinars</a>.
        <br><br>
        Sincerely,
        <br>
        The OSF Team

    </div>
</%def>
<%def name="footer()">
    <br>
    The <a href="${domain}">OSF</a> is provided as a free, open source service from the <a href="https://cos.io/">Center for Open Science</a>.
</%def>

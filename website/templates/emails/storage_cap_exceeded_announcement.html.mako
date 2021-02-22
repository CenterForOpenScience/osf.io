<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <%!
        from website import settings
    %>
    Hi ${user.given_name or user.fullname},<br>
    <br>
    Thank you for storing your research materials on OSF. We have updated the OSF Storage capacity to 5 GB for private content and 50 GB for public content. None of your current files stored on OSF Storage will be affected, but after November 3, 2020 projects exceeding capacity will no longer accept new file uploads.
    <br>
    <br>
    % if private_nodes:
    The following private projects and components have exceeded the 5 GB OSF Storage allotment and require your action:
    <ul>
      % for node in private_nodes:
        <li> <a href="${settings.DOMAIN.rstrip('/') + node.url}">${node.title}</a>
      % endfor
    </ul>
    <br>
    % endif
    % if public_nodes:
    The following public projects and components have exceeded the 50 GB OSF Storage allotment and require your action:
    <ul>
      % for node in public_nodes:
        <li> <a href="${settings.DOMAIN.rstrip('/') + node.url}">${node.title}</a>
      % endfor
    </ul>
    <br>
    % endif
    <strong>In order to avoid disruption to your workflow, please take action through one of the following options:</strong><br>
    <ul>
      <li>Connect an <a href="https://help.osf.io/hc/en-us/sections/360003623833-Storage-add-ons">OSF storage add-on</a> to continue managing your research efficiently from OSF. OSF add-ons are an easy way to extend your storage space while also streamlining your data management workflow.</li>
      % if private_nodes:
      <li><a href="https://help.osf.io/hc/en-us/articles/360018981414-Control-Your-Privacy-Settings#Make-your-project-or-components-public">Make your private project public</a> to increase storage capacity to 50 GB for files stored in OSF storage.</li>
      % endif
      <li><a href="https://help.osf.io/hc/en-us/articles/360019737614-Create-Components">Organize your project with components</a> to take advantage of the flexible structure and maximize storage options.</li>
    </ul>
    <br>
    Learn more about OSF Storage capacity <a href="https://help.osf.io/hc/en-us/articles/360054528874-OSF-Storage-Caps">here</a>, or contact <a href="mailto:support@osf.io">support@osf.io</a> with any questions you may have.<br>
    <br>
    Thanks,<br>
    <br>
    The OSF Team<br>
    <br>
</tr>
</%def>

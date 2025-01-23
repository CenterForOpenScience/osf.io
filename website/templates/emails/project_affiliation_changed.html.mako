<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    The affiliation of your project has changed.<br>
    <br>
    Affiliation changes:<br>
    % if institution_added:
      - Added: ${', '.join([inst.name for inst in institution_added])}<br>
    % endif
    % if institution_removed:
      - Removed: ${', '.join([inst.name for inst in institution_removed])}<br>
    % endif
    <br>
    Current affiliations: ${', '.join([inst.name for inst in current_affiliations])}<br>
    <br>
    Want more information? Visit <a href="https://osf.io">OSF</a> to learn about OSF, or
    <a href="https://cos.io">COS</a> for information about its supporting organization,
    the Center for Open Science.<br>
    <br>
    Questions? Email <a href="mailto:contact@osf.io">contact@osf.io</a><br>
    <br>
    Sincerely yours,<br>
    <br>
    The OSF Robot<br>
  </td>
</tr>
</%def>

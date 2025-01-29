<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Hello ${user.fullname},<br>
    <br>
    % if institution_added:
      ${', '.join([inst.name for inst in institution_added])} affiliation has been added to
      <a href=${node.absolute_url}>${node.title}</a>
    % endif
    % if institution_removed:
      ${', '.join([inst.name for inst in institution_removed])} affiliation has been removed from
      <a href=${node.absolute_url}>${node.title}</a>
    % endif
    <br>
    ${', '.join([inst.name for inst in current_affiliations])} are  current affiliations for
    <a href=${node.absolute_url}>${node.title}</a>.
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

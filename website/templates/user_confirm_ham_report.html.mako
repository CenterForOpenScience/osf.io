<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 style="padding: 0; margin: 30px 0 10px 0; font-weight: 400;">
      Confirm HAM finished for user ${user_guid}
    </h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
% if failed_ham:
    <p style="margin: 0;">Failed nodes/preprints: ${failed_ham}</p>
% endif
  </td>
</tr>
</%def>

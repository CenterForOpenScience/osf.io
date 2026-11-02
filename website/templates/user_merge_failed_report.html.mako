<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 style="padding: 0; margin: 30px 0 10px 0; font-weight: 400;">
      Merge of user ${mergee_guid} into ${merger_guid} failed
    </h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    <p style="margin: 0;">No changes were made to either account.</p>
% if error:
    <p style="margin: 10px 0 0 0;">Error: ${error}</p>
% endif
  </td>
</tr>
</%def>

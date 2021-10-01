<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Registrations Were Not Bulk Uploaded to your Community's Registry</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      Hello ${fullname},<br>
      <br>
      All ${count} registrations could not be uploaded. Errors are listed below. Review the file and try to upload the registrations again. Contact the Help Desk at support@osf.io if you continue to have issues.<br>
      <br>
      <ul>
          % for error in draft_errors:
              <li>${error}</li>
          % endfor
      </ul>
      <br>
      Sincerely,<br>
      <br>
      Open Science Framework Robot<br>
  </td>
</tr>
</%def>

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
      All ${count} registrations could not be uploaded due to duplicate rows found either within the uploaded csv file
      or in our system. Duplicates are listed below. Review the file and try to upload the registrations again after
      removing duplicates. Contact the Help Desk at <a href="mailto:${osf_support_email}">${osf_support_email}</a> if
      you continue to have issues.<br>
      <br>
      <ul>
          % for error in draft_errors:
              <li>${error}</li>
          % endfor
      </ul>
      <br>
      Sincerely,<br>
      <br>
      The OSF Team<br>
  </td>
</tr>
</%def>

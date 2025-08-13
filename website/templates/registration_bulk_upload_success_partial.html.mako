<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;"> Some Registrations Successfully Bulk Uploaded to your Community's Registry</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      Hello ${fullname},<br>
      <br>
      % if auto_approval:
          ${successes} out of ${total} of your registrations were successfully uploaded! Click the link below
          to begin moderating their recently submitted registrations.<br>
          <br>
          <a href="${pending_submissions_url}">${pending_submissions_url}</a><br>
      % else:
          ${successes} out of ${total} of your registrations were successfully uploaded! An email was recently sent
          out to all the admin contributors asking them to approve the registration. You may begin moderating the
          registrations once the registrations are approved by their contributors or after 48 hours have passed.<br>
      % endif
      <br>
      The remaining ${failures} registrations could not be uploaded and are listed below. Create a new csv file
      containing these registrations. Review the registrations and upload the file. Contact the Help Desk at
      <a href="mailto:${osf_support_email}">${osf_support_email}</a> if you continue to have issues.<br>
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

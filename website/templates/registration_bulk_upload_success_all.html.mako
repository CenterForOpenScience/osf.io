<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Registrations Successfully Bulk Uploaded to your Community's Registry</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      Hello ${user_fullname},<br>
      <br>
      % if auto_approval:
          All ${count} of your registrations were successfully uploaded! Click the link below to begin moderating the
          recently submitted registrations.<br>
          <br>
          <a href="${pending_submissions_url}">${pending_submissions_url}</a><br>
          <br>
      % else:
          All ${count} of your registration were successfully uploaded! An email was recently sent out to all the
          admin contributors asking them to approve the registration. You may begin moderating the registrations
          once the registrations are approved by their contributors or after 48 hours have passed.<br>
      % endif
      <br>
      Sincerely,<br>
      <br>
      The OSF Team<br>
  </td>
</tr>
</%def>

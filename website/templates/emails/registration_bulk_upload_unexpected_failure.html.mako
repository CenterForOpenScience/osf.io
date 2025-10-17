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
      Your registrations were not uploaded. Our team was notified of the issue and will follow up after they start
      looking into the issue. Contact the Help Desk at <a href="mailto:${osf_support_email}">${osf_support_email}</a>
      if you continue to have questions.<br>
      <br>
      Sincerely,<br>
      <br>
      The OSF Team<br>
  </td>
</tr>
</%def>

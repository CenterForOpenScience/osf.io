<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">
      Notification campaign [${campaign_name}]
    </h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      Notification campaign [${campaign_name}] has reached the following status:<br>
      <br>
      <strong>${status}</strong><br>
      <br>
      ${message}<br>
      Sincerely,<br>
      <br>
      The OSF Team<br>
  </td>
</tr>
</%def>
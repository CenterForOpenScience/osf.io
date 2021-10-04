<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Registry Could Not Bulk Upload Registrations</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      Hello,<br>
      <br>
      [${user}] from registry [${provider_name}] attempted to upload the registrations from a csv file. Review the
      file and inform the engineers of the issue. The registry has been notified of the problem and is waiting on a
      response. Below is the error message provided by the system.<br>
      <br>
      ${message}<br>
      <br>
      Sincerely,<br>
      <br>
      The OSF Team<br>
  </td>
</tr>
</%def>

<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Your submission of file [${query_file_name}] to Boa is successful</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      Hello ${fullname},<br>
      <br>
      Your submission of file [${query_file_name}] to Boa is successful.
      The result has been uploaded to OSF and stored in file [${output_file_name}]. <br>
      <br>
      The Boa job ID for this submission is [${job_id}].
      Visit Boa's job list page [${boa_job_list_url}] for more information. <br>
      <br>
      Sincerely,<br>
      <br>
      The OSF Team<br>
  </td>
</tr>
</%def>

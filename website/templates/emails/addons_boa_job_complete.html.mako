<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Your submission to Boa [${job_id}] is successful</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      Hello ${fullname},<br>
      <br>
      Your submission [${job_id}] of file [${query_file_full_path}] to Boa is successful. <br>
      <br>
      The result has been uploaded to OSF and stored in file [${output_file_name}] under the same folder where you submit the file.
      Visit <a href="${project_url}">your project</a> to access the result. <br>
      <br>
      In addition, the Boa job ID for this submission is [${job_id}]. Visit <a href="${boa_job_list_url}">Boa's job list page</a> for more information. <br>
      <br>
      Sincerely,<br>
      <br>
      The OSF Team<br>
  </td>
</tr>
</%def>

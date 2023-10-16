<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
    <td style="border-collapse: collapse;">
        <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Your submission of file [${query_file_name}] to Boa has failed</h3>
    </td>
</tr>
<tr>
    <td style="border-collapse: collapse;">
        Hello ${fullname},<br>
        <br>
        Your submission of file [${query_file_name}] to Boa has failed with the following error: <br>
        &emsp;${message} <br>
        % if query_error:
            Please fix your query file and try again. <br>
            For details, visit Boa's job list page (${boa_job_list_url}). The Boa job ID for this submission is [${job_id}]. <br>
        % elif is_complete:
            Your query has completed on Boa and the job ID is [${job_id}]. Visit Boa's job list page (${boa_job_list_url}) to retrieve the results. <br>
        % elif needs_config:
            Please fix your Boa addon configuration on OSF and/or your Boa account on Boa before trying again. <br>
        % else:
            Please try again later. If this issue persists, contact the Help Desk at <a href="mailto:${osf_support_email}">${osf_support_email}</a>. <br>
        % endif
        <br>
        Sincerely,<br>
        <br>
        The OSF Team<br>
    </td>
</tr>
</%def>

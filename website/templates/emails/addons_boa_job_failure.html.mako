<%inherit file="notify_base.mako" />
<%def name="content()">
<tr>
    <td style="border-collapse: collapse;">
        <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Your submission to Boa has failed</h3>
    </td>
</tr>
<tr>
    <td style="border-collapse: collapse;">
        Hello ${fullname},<br>
        <br>
        Your submission of file [${query_file_name}] from <a href="${project_url}">your OSF project</a> to Boa has failed. <br>
        <br>
        % if code == 1:
            The query you submitted encountered compile or run-time error. Please fix your query file and try again. <br>
            <br>
            For details, visit <a href="${boa_job_list_url}">Boa's job list page</a>. The Boa job ID for this submission is [${job_id}]. <br>
        % elif code == 2:
            Your query has completed on Boa and the job ID is [${job_id}]. However, we were not able to upload the result to OSF. <br>
            <br>
            Visit <a href="${boa_job_list_url}">Boa's job list page</a> to retrieve the results. <br>
        % elif code == 3:
            OSF can not log in to Boa. Please fix your Boa addon configuration on OSF and try again. <br>
        % else:
            OSF encountered an unexpected error when connecting to Boa. Please try again later. <br>
            <br>
            If this issue persists, contact OSF Help Desk at <a href="mailto:${osf_support_email}">${osf_support_email}</a> and attach the following error message. <br>
            <br>
            ${message} <br>
        % endif
        <br>
        Sincerely,<br>
        <br>
        The OSF Team<br>
    </td>
</tr>
</%def>

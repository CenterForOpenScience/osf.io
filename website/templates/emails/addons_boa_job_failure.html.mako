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
        Your submission of file [${query_file_full_path}] from <a href="${project_url}">your OSF project</a> to Boa has failed. <br>
        <br>
        % if code == 1:
            OSF cannot log in to Boa. Please fix your Boa addon configuration on OSF and try again. <br>
            <br>
            For details, visit <a href="${boa_job_list_url}">Boa's job list page</a>. The Boa job ID for this submission is [${job_id}]. <br>
        % elif code == 2:
            The query you submitted encountered compile or run-time error. Please fix your query file and try again. <br>
            <br>
            For details, visit <a href="${boa_job_list_url}">Boa's job list page</a>. The Boa job ID for this submission is [${job_id}]. <br>
        % elif code == 3:
            Your query has completed on Boa and the job ID is [${job_id}]. <br>
            <br>
            However, we were not able to upload the result to <a href="${project_url}">your OSF project</a> because an existing output file [${output_file_name}] already exists. <br>
            <br>
            Please either rename your query file or remove the existing result file and try again. <br>
            <br>
            In addition, you can visit <a href="${boa_job_list_url}">Boa's job list page</a> to retrieve the results. <br>
        % elif code == 4:
            Your query has completed on Boa and the job ID is [${job_id}]. However, we were not able to upload the result to OSF. <br>
            <br>
            Visit <a href="${boa_job_list_url}">Boa's job list page</a> to retrieve the results. <br>
        % elif code == 5:
            Your query has completed on Boa and the job ID is [${job_id}]. However, we were not able to retrieve the output from Boa. <br>
            <br>
            A common cause of this failure is that the output is empty. Visit <a href="${boa_job_list_url}">Boa's job list page</a> to check if the output is empty. <br>
            <br>
            If you believe this is in error, contact Boa Support at <a href="mailto:${boa_support_email}">${boa_support_email}</a>. <br>
        % elif code == 6:
            OSF cannot submit your query file to Boa since it is too large: [${file_size} Bytes] is over the maximum allowed threshold [${max_file_size} Bytes]. <br>
            <br>
            If you believe this is in error, contact OSF Help Desk at <a href="mailto:${osf_support_email}">${osf_support_email}</a>. <br>
        % elif code == 7:
            It's been ${max_job_wait_hours} hours since we submitted your query job [${job_id}] to Boa. <br>
            <br>
            However, OSF haven't received confirmation from Boa that the job has been finished. <br>
            <br>
            Visit <a href="${boa_job_list_url}">Boa's job list page</a> to check it's status. <br>
            <br>
            If you believe this is in error, contact OSF Help Desk at <a href="mailto:${osf_support_email}">${osf_support_email}</a>. <br>
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

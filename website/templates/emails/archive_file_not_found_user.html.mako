<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Issue registering <a href="${domain.rstrip('/')+ src.url}">${src_title}</a></h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    Your registration for the project ${src_title} at ${src.absolute_url} failed because one of more of the following files have been altered since you attached them to the draft registration. To fix this problem, please go to <a href="${results['draft'].absolute_url}">your draft registration</a> and select the files you want to be included in your registration.
    <br />
    <ul>
      % for missing in results['missing_files']:
      <li>
        ${missing['file_name']} on question "${missing['question_title']}"
      </li>
      % endfor
    </ul>
  </td>
</tr>
</%def>

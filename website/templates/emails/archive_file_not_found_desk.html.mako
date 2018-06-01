<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <% from website import settings %>
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Issue registering <a href="${settings.DOMAIN.rstrip('/')+ src.url}">${src.title}</a></h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    User: ${user.fullname} (${user.username}) [${user._id}]

    Tried to register ${src.title} (${url}) [${src._id}], but the archive task failed when copying files. At least one file selected in the registration schema was moved or deleted in between its selection and archival.
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

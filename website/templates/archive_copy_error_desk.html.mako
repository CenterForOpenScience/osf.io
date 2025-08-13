<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Issue registering <a href="${src_url}">${src_title}</a></h3>

  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      User: ${user_fullname} (${user_username}) [${user__id}]

      Tried to register ${src_title} (${url}) [${src__id}], but the archive task failed when copying files.

    <br />
      A report is included below:
    <% import json %>

    % for addon in results:
    <ul>${addon['name']}: - ${addon['status']}
        % for err in addon['errors']:
            <li> ${json.dumps(err)}</li>
        % endfor
    </ul>
    % endfor
  </td>
</tr>
</%def>

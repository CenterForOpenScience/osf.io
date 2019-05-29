<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <% from website import settings %>
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Issue registering <a href="${settings.DOMAIN.rstrip('/') + src.url}">${src.title}</a></h3>

  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      User: ${user.fullname} (${user.username}) [${user._id}]

      Tried to register ${src.title} (${url}) [${src._id}], but the archive task failed when copying files.

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

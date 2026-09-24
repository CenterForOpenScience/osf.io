<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">${stuck_count} registrations have not finished archiving</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    Restarted ${restarted_count} of them. The rest could not be restarted and need a person.

    A registration that was restarted but shows up here again tomorrow did not archive, so it needs a person too.

    <br />
    <ul>
        % for registration in registrations:
            <li><a href="${registration['url']}">${registration['registration__id']}</a>: ${registration['result']}</li>
        % endfor
    </ul>
  </td>
</tr>
</%def>

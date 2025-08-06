<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">
      Recent Activity
    </h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    % if notifications:
      <table class="block" width="100%" border="0" cellpadding="15" cellspacing="0" align="center">
        <tbody>
          % for n in notifications:
            <tr>
              <td style="border-collapse: collapse;">
                ${n}
              </td>
            </tr>
          % endfor
        </tbody>
      </table>
    % else:
      <p>No recent activity.</p>
    % endif
  </td>
</tr>
</%def>

<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">

    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">The fork of <b>${node_title}</b> has been successfully created here: <a href="${domain}${node__id}">${domain} ${node__id}</a> </h3>
  </td>
</tr>
</%def>

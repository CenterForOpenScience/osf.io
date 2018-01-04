<%inherit file="notify_base.mako" />


<%def name="content()">
<% from api.base import settings %>
<tr>
  <td style="border-collapse: collapse;">

    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">The fork of <b>${title}</b> has been successfully created here: <a href="${settings.DOMAIN + guid}">${settings.DOMAIN + guid}</a> </h3>
  </td>
</tr>
</%def>

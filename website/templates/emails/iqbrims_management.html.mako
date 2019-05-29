<%inherit file="notify_base.mako" />


<%def name="content()">
<% from website import settings %>
<tr>
  <td style="border-collapse: collapse;">

    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">
      ${notify_type}
    </h3>
    <a href="${settings.DOMAIN + guid}">${settings.DOMAIN + guid}</a>
  </td>
</tr>
</%def>

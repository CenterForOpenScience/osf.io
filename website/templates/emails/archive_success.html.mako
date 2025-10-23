<%inherit file="notify_base.mako" />


<%def name="content()">
<% from website import settings %>
<tr>
  <td style="border-collapse: collapse;">

    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Registration of <b><a href="${settings.DOMAIN.rstrip('/') + src.url}">${src.title}</a></b> finished</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    You can view the registration <a href="${settings.DOMAIN.rstrip('/') + src.url}">here.</a>
  </td>
</tr>
</%def>

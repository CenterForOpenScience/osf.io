<%inherit file="notify_base.mako" />


<%def name="content()">
<% from website import settings %>
<tr>
  <td style="border-collapse: collapse;">

    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Your fork <b>${title}</b> has finished</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    You can view the fork here <a href="${settings.DOMAIN + guid}">here.</a>
  </td>
</tr>
</%def>

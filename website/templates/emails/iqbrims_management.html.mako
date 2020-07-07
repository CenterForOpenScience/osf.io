<%inherit file="notify_base.mako" />


<%def name="content()">
<% from website import settings %>
<tr>
  <td style="border-collapse: collapse;">

    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">
      ${notify_title}
    </h3>
    <p>
      ${notify_body}
    </p>
  </td>
</tr>
</%def>

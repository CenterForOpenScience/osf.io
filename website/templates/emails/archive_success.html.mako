<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">

    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Registration of <b><a href="${src_url}">${src_title}</a></b> finished</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    You can view the registration <a href="${src_url}">here.</a>
  </td>
</tr>
</%def>

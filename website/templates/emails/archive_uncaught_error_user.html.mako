<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Issue registering <a href="${src_url}"> ${src_title}</a></h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    We cannot archive ${src_title} at this time because there were errors copying files to the registration. Our development team is investigating this failure. We're sorry for any inconvenience this may have caused.
  </td>
</tr>
</%def>

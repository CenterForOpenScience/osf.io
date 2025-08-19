<%inherit file="notify_base.mako" />

<%def name="content()">
<% from website import settings %>
<tr>
  <td style="border-collapse: collapse;">
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Issue registering <a href="${settings.DOMAIN.rstrip('/') + src.url}">${src.title}</a></h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    Hi,
    We couldn’t complete the registration for ${src.title} because its' size exceeds your limit of ${str(draft_registration.custom_storage_usage_limit).rstrip('0')}GB.
  </td>
</tr>
</%def>

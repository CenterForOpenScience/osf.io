<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <% from website import settings %>
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Issue registering <a href="${settings.DOMAIN.rstrip('/') + src.url}">${src.title}</a></h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    We cannot archive ${src.title} at this time because the projected size of the registration exceeds our usage limits. You should receive a followup email from our support team shortly. We're sorry for any inconvenience this may have caused.
  </td>
</tr>
<tr >
    <td style="border-collapse: collapse;" align="left">
        <br>
        Center for Open Science<br>
        210 Ridge McIntire Road<br>
        Suite 500<br>
        Charlottesville, VA 22903-5083<br>
    </td>
</tr>
</%def>

<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Issue registering ${src.title}</h3> 
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    We cannot archive ${src.title} at this time because the projected size of the registration exceeds our usage limits. You should be recieving a followup email from our support team shortly. We're sorry for any inconvience this may have caused. 
  </td>
</tr>
</%def>

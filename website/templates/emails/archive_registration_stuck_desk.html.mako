<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">${len(broken_registrations)} registrations found stuck in archiving</a></h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    See attached file for details.

    Automatically sent from scripts/stuck_registration_audit.py
  </td>
</tr>
</%def>

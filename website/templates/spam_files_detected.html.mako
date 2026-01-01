<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">${ct} spammy files found matching ${sniff_r}</a></h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
    See attached file for details.

    Automatically sent from osf/management/commands/find_spammy_files.py
  </td>
</tr>
</%def>

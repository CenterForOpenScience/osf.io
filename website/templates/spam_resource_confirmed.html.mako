<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Dear ${user_fullname}, <br>
    <br>
    Your ${resource_type_label} "${resource_title}" on the Open Science Framework has been flagged as spam and made private: ${resource_absolute_url}<br>
    If this is in error, please email ${osf_support_email} for assistance.<br>
    <br>
    Regards,<br>
    <br>
    The OSF Team<br>

</tr>
</%def>

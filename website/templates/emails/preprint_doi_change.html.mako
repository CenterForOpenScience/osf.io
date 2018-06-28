<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Dear ${user.fullname},<br>
    <br>
    We're writing to let you know about an improvement to the OSF Preprints family of preprint services.
    Soon, OSF Preprints and the branded community preprint services it supports will begin registering DOIs with Crossref.
    We're making this change to take advantage of Crossref's preprints-specific metadata schema, linking of published articles with preprints,
    and auto-updating of ORCID profiles (if you've verified your account by logging into the OSF via ORCID).<br>
    <br>
    In the coming days, we'll register your existing preprints with Crossref and they'll be given new DOIs, displayed on your preprint page.
    The current DOIs on your preprints will be aliased and will always resolve to your preprint; however, we recommend that in future citations you use the new DOIs.
    For a period of time during the re-registering process, your preprint may have 2 distinct DOI records.<br>
    <br>
    DOIs for projects and registrations on the OSF will continue to be registered with DataCite and you will not see any changes to these.<br>
    <br>
    Please email <a href="mailto:support@osf.io">support@osf.io</a> if you have questions or concerns.<br>
    <br>
    Sincerely,<br>
    <br>
    The OSF Team<br>
    <br>
    <br>
    You are receiving this service message from OSF because you are an author on a preprint.<br>

</tr>
</%def>

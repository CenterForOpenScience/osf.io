<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Welcome to the OSF!</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">

Hello ${user.fullname},<br>
<br>
Thank you for verifying your OSF account, a free, open source service maintained by the Center for Open Science. Here are a few things you can do with the OSF:<br>
<br>
<h4>Store your files</h4>
Archive your materials, data, manuscripts, or anything else associated with your research during the research process or after it is complete.<br>
<br>
<h4>Affiliate your projects with your institution</h4>
Associate your projects with your institution. They will be added to your institution's central commons, improving discoverability of your work and fostering collaboration.<br>
<h4>Share your work</h4>
Keep your research materials and data private, make it accessible to specific others with view-only links, or make it publicly accessible. You have full control of what parts of your research are public and what remains private.<br>
<br>
<h4>Register your research</h4>
Create a permanent, time-stamped version of your projects and files.  Do this to preregister your design and analysis plan to conduct a confirmatory study, or archive your materials, data, and analysis scripts when publishing a report.<br>
<br>
<h4>Make your work citable</h4>
Every project and file on the OSF has a permanent unique identifier, and every registration can be assigned a DOI.  Citations for public projects are generated automatically so that visitors can give you credit for your research.<br>
<br>
<h4>Measure your impact</h4>
You can monitor traffic to your public projects and downloads of your public files.<br>
<br>
<h4>Connect services that you use</h4>
GitHub, Dropbox, Google Drive, Box, Dataverse, figshare, Amazon S3, ownCloud, Bitbucket, GitLab, OneDrive, Mendeley, Zotero.  Do you use any of these? Link the services that you use to your OSF projects so that all parts of your project are in one place.<br>
<br>
<h4>Collaborate</h4>
Add your collaborators to have a shared environment for maintaining your research materials and data and never lose files again.<br>
<br>
<br>
Learn more about the OSF at our <a href="http://help.osf.io">Guides page</a>, or email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a> with questions for support.<br>
<br>
Sincerely,<br>
<br>
The Center for Open Science Team<br>

  </td>
</tr>
</%def>

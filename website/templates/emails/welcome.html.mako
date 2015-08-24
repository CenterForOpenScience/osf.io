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
    Thank you for verifying your OSF account. You are now ready to store your work, manage your projects, and collaborate within the OSF. Here are a few ways scholars work with us:<br>
<br>
    <h4>Project Management</h4>
    The OSF allows you to view all of your projects from a single dashboard, and to organize elements of your projects with components. You can organize your projects in whichever way works best for you, by members of your lab, to parts of a larger research undertaking.<br>
<br>
    <h4>Collaboration</h4>
    The OSF was built from the ground up with collaboration in mind. Files stored in your projects are versioned, so no more emailing files back and forth with ever expanding suffixes. You control who has access to your projects and what they can see.<br>
<br>
    <h4>Archiving</h4>
    You can make permanent, time stamped snapshots of your projects whenever you want. About to start collecting data? Register your project to demonstrate that your hypotheses and methods weren't influenced by your data. About to submit for publication? Register and keep a record of your first submission. Data stored on the OSF are guaranteed by an endowment to make sure your work is preserved in perpetuity.<br>
<br>
    These are just a few of the things that the Open Science Framework can do for you. You can browse <a href="https://osf.io/explore/activity/#popularPublicProjects">popular public projects</a> for more inspiration. Learn more <a href="https://osf.io/getting-started/">here</a>, and do not hesitate to <a href="mailto:contact@cos.io">contact us</a> with questions.<br>
<br>
    Sincerely,<br>
    Brian Nosek and Jeff Spies<br>
    Founders, The Center for Open Science
  </td>
</tr>
</%def>

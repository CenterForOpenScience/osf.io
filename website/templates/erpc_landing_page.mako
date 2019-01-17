<%inherit file="base.mako"/>

<%def name="title()">GakuNin RDM Election Research Preacceptance Competition</%def>

<%def name="stylesheets()">
    ${ parent.stylesheets() }
    <link rel="stylesheet" href="/static/css/prereg.css">
</%def>

<%def name="content()">
<div class="prereg-container">
    <h1 class="m-t-xl m-b-lg text-center">The Election Research Preacceptance Competition is Now Closed</h1>
    <p>With the release of the <a href="http://www.electionstudies.org/">American National Election Studies</a>
        2016 survey dataset, no additional preregistrations are being accepted for this competition.
        To read more about this competition and its current status, please visit <a href="https://www.erpc2016.com">www.erpc2016.com</a>.</p>
    <br>
    <p>To see the publicly available preregistrations created as part of this initiative, please see
        <a href="https://rdm.nii.ac.jp/registries/discover?provider=GakuNin RDM&type=Election%20Research%20Preacceptance%20Competition">GakuNin RDM Registries</a>.
        Please note that many studies created as part of this competition will remain private for up to four years from the date of creation.
    </p>
    <br>
    <p>A blank version of the Election Research Preacceptance Competition form is available <a href="https://rdm.nii.ac.jp/pu4xc/">here</a>. </p>
    <br>
    <p>If you'd like to preregister another study, please see the Preregistration Challenge
        <a href="https://nii.ac.jp/prereg/">information page</a> or get started on your next preregistration
        <a href="https://rdm.nii.ac.jp/prereg/">now</a>.
    </p>

</div>
</%def>
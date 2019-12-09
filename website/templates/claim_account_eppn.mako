<%inherit file="base.mako"/>
<%def name="title()">${_("Claim Contributor")}</%def>
<%def name="content()">
<h1 class="page-header text-center">${_("Claim Contributor")}</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
    <p>${_("Please confirm to continue.")}</p>

        <form method="POST" id='claimContributorForm' role='form'>
	    ${_("Full name (can be changed later):")}
            <div class='form-group'>
                <input type="text" class='form-control' value="${fullname}" disabled/>
            </div>
	    ${_("Primary Email (Username) (can be changed later):")}
            <div class='form-group'>
                <input type="text" class='form-control' value="${username}" disabled/>
            </div>
	    % if alternate_email:
	    ${_("Alternate Email (can be changed later):")}
            <div class='form-group'>
                <input type="text" class='form-control' value="${alternate_email}" disabled/>
            </div>
	    % endif
            <span class='help-text'>
                <a id="signOutLink" href='${signOutUrl}'>${_("I am <strong>not</strong> <em>%(username)s</em>.") % dict(username=h(username)) | n}</a>
            </span>
            <button type='submit' class="btn btn-submit btn-primary pull-right">${_("Continue")}</button>
        </form>

    </div>
</div>
</%def>


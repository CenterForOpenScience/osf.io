<%inherit file="base.mako"/>
<%def name="title()">Claim Contributor</%def>
<%def name="content()">
<h1 class="page-header text-center">Claim Contributor</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
    <p>Please confirm to continue.</p>

        <form method="POST" id='claimContributorForm' role='form'>
	    Full name (can be changed later):
            <div class='form-group'>
                <input type="text" class='form-control' value="${fullname}" disabled/>
            </div>
	    Primary Email (Username) (can be changed later):
            <div class='form-group'>
                <input type="text" class='form-control' value="${username}" disabled/>
            </div>
	    % if alternate_email:
	    Alternate Email (can be changed later):
            <div class='form-group'>
                <input type="text" class='form-control' value="${alternate_email}" disabled/>
            </div>
	    % endif
            <span class='help-text'>
                <a id="signOutLink" href='${signOutUrl}'>I am <strong>not</strong> <em>${username}</em>.</a>
            </span>
            <button type='submit' class="btn btn-submit btn-primary pull-right">Continue</button>
        </form>

    </div>
</div>
</%def>


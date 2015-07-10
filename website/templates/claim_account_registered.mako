<%inherit file="base.mako"/>
<%def name="title()">Claim Contributor</%def>
<%def name="content()">
<h1 class="page-header text-center">Claim Contributor</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
    <p>Please enter your credentials to continue.</p>

        <form method="POST" id='claimContributorForm' role='form'>
            <div class='form-group'>
                <input type="text" class='form-control' value="${user.username}" disabled/>
            </div>
            <div class='form-group'>
                ${form.password(placeholder='Password', autofocus=True)}
            </div>

            %if next_url:
                <input type='hidden' name='next_url' value='${next_url}'>
            %endif
            <span class='help-text'>
                <a id="signOutLink" href='${signOutUrl}'>I am <strong>not</strong> <em>${user.fullname}</em>.</a>
            </span>
            <button type='submit' class="btn btn-submit btn-primary pull-right">Continue</button>
        </form>

    </div>
</div>
</%def>


<%inherit file="base.mako"/>
<%def name="title()">${_("Claim Contributor")}</%def>
<%def name="content()">
<h1 class="page-header text-center">${_("Claim Contributor")}</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
    <p>${_("Please enter your credentials to continue.")}</p>

        <form method="POST" id='claimContributorForm' role='form'>
            <div class='form-group'>
                <input type="text" class='form-control' value="${user.username}" disabled/>
            </div>
            <div class='form-group'>
                ${form.password(placeholder='Password', autofocus=True) | unicode, n }
            </div>

            %if next_url:
                <input type='hidden' name='next_url' value='${next_url}'>
            %endif
            <span class='help-text'>
                <a id="signOutLink" href='${signOutUrl}'>${_("I am <strong>not</strong> <em>%(userFullname)s</em>.</a>") % dict(userFullname=h(user.fullname)) | n}
            </span>
            <button type='submit' class="btn btn-submit btn-primary pull-right">${_("Continue")}</button>
        </form>

    </div>
</div>
</%def>


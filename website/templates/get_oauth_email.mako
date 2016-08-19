<%inherit file="base.mako"/>
<%def name="title()">OSF ORCID Login</%def>
<%def name="content()">
<h1 class="page-header text-center">OSF ORCID Login | Almost Done</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
        <p class='help'>
            Please enter you email to finalize the login.
            If you already have an OSF account, this will link your ORCID profile with OSF.
            If not, this will create an new account for you with your ORCID profile.
        </p>

        <form id='resendForm' method='POST' class='form' role='form'>
            <div class='form-group'>
                ${form.email(placeholder='Email address', autofocus=True) | unicode, n }
            </div>

            <button type='submit' class='btn btn-primary'>Send</button>
        </form>
    </div>
</div>
</%def>

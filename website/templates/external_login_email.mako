<%inherit file="base.mako"/>
<%def name="title()">GakuNin RDM ${external_id_provider} Login</%def>
<%def name="content()">
<h1 class="page-header text-center">GakuNin RDM ${external_id_provider} Login | Register Email</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
        <p class='help'>
            Please enter your email to finalize the login.
            If you already have an GakuNin RDM account, this will link your ${external_id_provider} profile with GakuNin RDM.
            If not, this will create a new account for you with your ${external_id_provider} profile.
        </p>

        <form id='resendForm' method='POST' class='form' role='form'>
            <div class='form-group'>
                ${form.email(placeholder='Email address', autofocus=True) | unicode, n }
            </div>
            <button type='submit' class='btn btn-primary'>Send</button>
            <a href='/logout' class='btn btn-danger'>Cancel</a>
        </form>
    </div>
</div>
</%def>

<%inherit file="base.mako"/>
<%def name="title()">OSF ${external_id_provider} Login</%def>
<%def name="content()">
<h1 class="page-header text-center">OSF ${external_id_provider} Login | Register Email</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
        <p class='help'>
            Please enter your email to finalize the login.
            If you already have an OSF account, this will link your ${external_id_provider} profile with OSF.
            If not, this will create a new account for you with your ${external_id_provider} profile.
        </p>

        <form id='resendForm' method='POST' class='form' role='form'>
            <div class='form-group'>
                ${form.email(placeholder='Email address', autofocus=True, required=True) | unicode, n }
            </div>
            % if not auth_user_fullname:
                <div class='form-group'>
                    ${form.name(placeholder='Full name', autofocus=True, required='required') | unicode, n }
                </div>
            % endif
            <div class='form-group'>
                ${form.accepted_terms_of_service(required='required') | unicode, n }
                <label>I have read and agree to the <a target="_blank" href='https://github.com/CenterForOpenScience/cos.io/blob/master/TERMS_OF_USE.md'>Terms of Use</a> and <a target="_blank" href='https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md'>Privacy Policy</a>.</label>
            </div>
            <button type='submit' class='btn btn-primary'>Send</button>
            <a href='/logout' class='btn btn-danger'>Cancel</a>
        </form>
    </div>
</div>
</%def>

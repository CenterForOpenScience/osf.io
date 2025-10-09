<%inherit file="base.mako"/>
<%def name="title()">OSF ${external_id_provider} Login</%def>
<%def name="content()">
<h1 class="page-header text-center">Sign In With ${external_id_provider}</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
        <p>
            Please enter your email to finalize your ${external_id_provider} login.
        </p>
        <p>
            If you already have an OSF account, this will link your ${external_id_provider} profile with OSF.
            If not, this will create a new account for you with your ${external_id_provider} profile.
        </p>

        <form id='resendForm' method='POST' class='form' role='form'>
            % if not auth_user_fullname:
                <div class='form-group'>
                    Full name:
                    ${form.name(placeholder='Albert Einstein', autofocus=True, required='required') | unicode, n }
                </div>
            % endif
            <div class='form-group'>
                Email address:
                ${form.email(placeholder='support@osf.io', autofocus=True, required=True) | unicode, n }
            </div>
            <div class='form-group'>
                ${form.accepted_terms_of_service(required='required') | unicode, n }
                <label>I have read and agree to the <a target="_blank" href='https://github.com/CenterForOpenScience/cos.io/blob/master/TERMS_OF_USE.md'>Terms of Use</a> and <a target="_blank" href='https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md'>Privacy Policy</a>.</label>
            </div>
            <div class='border-top flex-row gap-1 padding-top-2'>
                <a href='/logout' class='btn btn-secondary flex-grow-1'>Cancel</a>
                <button type='submit' class='btn btn-primary flex-grow-1'>Send</button>
            </div>
        </form>
    </div>
</div>
</%def>

<%inherit file="base.mako"/>
<%def name="title()">Claim Account</%def>
<%def name="content()">
<h1 class="page-header text-center">Set Password</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
    <p>Hello ${ firstname }! Please set a password to claim your account.</p>
    <p>E-mail: <strong>${ email }</strong></p>

        <form method="POST" id='setPasswordForm' role='form'>
            <div class='form-group'>
                ${form.password(placeholder='New password') | unicode, n }
            </div>
            <div class='form-group'>
                ${form.password2(placeholder='New password again') | unicode, n }
            </div>
            ${form.token | unicode, n }
            %if next_url:
                <input type='hidden' name='next_url' value='${next_url}'>
            %endif
            <button type='submit' class="btn btn-success pull-right">Save</button>
        </form>

        <div class='help-block'>
            <p>If you are not ${fullname}, or if you were erroneously added as a contributor to the project described in the email invitation, please email <a href="mailto:contact@osf.io">contact@osf.io</a>
            </p>
            <p>By clicking "Save" and creating an account you agree to our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/TERMS_OF_USE.md">Terms</a> and that you have read our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>, including our information on <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md#f-cookies">Cookie Use</a>.</p>
        </div>
    </div>
</div>
</%def>

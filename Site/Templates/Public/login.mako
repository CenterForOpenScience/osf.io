<%inherit file="contentContainer.mako" />
<% import Framework %>
<div class="page-header">
    <h1>Create an Account or Sign-In</h1>
</div>
<div class="row">
    <div class="span1">&nbsp;</div>
    <div class="span6">
        <h2>Create Account</h2>
        <%include file="form.mako" args="
            form=form_registration, 
            name='registration',
            actionString='/register', 
            formClass='form-stacked', 
            submitString='Create Account',
            fieldNamePrefix='register_',
        "/>
     </div>
     <div class="span4">
         <h2>Sign-In</h2>
         <%include file="form.mako" args="
            form=form_signin,
            name='signin',
            actionString='/login', 
            formClass='form-stacked', 
            submitString='Sign In',
        "/>
        <hr />
        <h3>Forgot Password</h3>
        <%include file="form.mako" args="
            form=form_forgotpassword,
            name='forgotpassword', 
            actionString='/forgotpassword', 
            formClass='form-stacked', 
            submitString='Reset Password'
        "/>
    </div>
    <div class="span1">&nbsp;</div>
</div>

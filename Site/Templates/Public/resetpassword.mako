<%inherit file="contentContainer.mako" />

<div class="page-header">
    <h1>Reset Password</h1>
</div>
<div class="row">
    <div class="span1">&nbsp;</div>
    <div class="span6">
        <%include file="form.mako" args="
            form=form_resetpassword,
            name='resetpassword', 
            actionString='/resetpassword/' + verification_key, 
            formClass='form-stacked', 
            submitString='Reset Password'
        "/>
     </div>
     <div class="span4">&nbsp;</div>
    <div class="span1">&nbsp;</div>
</div>

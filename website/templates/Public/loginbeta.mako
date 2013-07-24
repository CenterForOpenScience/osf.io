<%inherit file="contentContainer.mako" />

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
            actionString='/registerbeta', 
            formClass='form-stacked', 
            submitString='Create Account'
        "/>
     </div>
     <div class="span4">
         &nbsp;
    </div>
    <div class="span1">&nbsp;</div>
</div>

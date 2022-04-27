<%inherit file="base.mako"/>
<%def name="title()">${_('Activate code')}</%def>
<%def name="content()">
<h1 class="page-header text-center">${_('Activate code')}</h1>

<div class="row">
    <div class="col-md-6 col-md-offset-3 text-center">
        <p class="text-left">${_('The Invitation Code has expired...')}<br>
            ${_('Please click the button below if you would like to receive an invitation to the project again.')}</p>
        <br>
        <br>
        <a class="btn btn-success" href="${url}">${_('Activate code')}</a>
    </div>
</div>
</%def>

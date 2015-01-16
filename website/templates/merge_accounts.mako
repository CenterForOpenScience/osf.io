<%inherit file="base.mako"/>
<%def name="title()">Merge Accounts</%def>
<%def name="content()">
<h1 class="page-header text-center">Merge with Duplicate Account</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
            <div mod-meta='{
            "tpl": "util/render_form.mako",
            "uri": "/user/merge/",
            "kwargs": {
                "id": "mergeAccountsForm",
                "name": "mergeAccounts",
                "method_string": "POST",
                "action_string": "#",
                "form_class": "form",
                "submit_string": "Merge Accounts",
                "field_name_prefix": "merged_",
                "submit_btn_class": "btn-success"
            },
            "replace": true
            }'>
            </div>
    </div>
</div>
</%def>

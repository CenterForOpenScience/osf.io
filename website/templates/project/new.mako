<%inherit file="base.mako"/>
<%def name="title()">Create New Project</%def>
<%def name="content()">
<h2 class="page-title text-center">Create New Project</h2>
<div class="row">
    <div class="col-md-6 col-md-offset-3">
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/new_project/",
                "kwargs": {
                    "name": "newProject",
                    "method_string": "POST",
                    "action_string": "/project/new/",
                    "form_class": "form-stacked",
                    "submit_string": "Create New Project",
                    "id": "projectForm",
                    "submit_btn_class": "btn-primary"
                },
                "replace": true
            }'>
        </div>
    </div>
</div><!-- end row -->
<script>
$(function() {

    var old_elem = $('#template');
    var id = old_elem.attr('id');

    var replace_with = function(el) {
        old_elem.hide()
        var old_field = old_elem.data('replacement');
        if(typeof(old_field) !== 'undefined') {
            old_field.remove()
        }
        old_elem.data('replacement', el)
        old_elem.after(el)
        el.data('replaces', old_elem)
    }

    var replace_with_input = function() {
        input = $('<div class="input-group">' +
                '<input class="form-control"/>' +
                '<span class="input-group-btn">' +
                    '<button class="btn btn-default">' +
                        '<span class="caret"/>' +
                    '</button>' +
                '</span>' +
            '</div>');

        cache = {
            '': [{
                authors: "<a href=\"/28ce4/\">Test One</a>",
                category: "My Projects",
                id: "jbk7n",
                label: "Fake",
                value: "Fake",
            }]
        };

        input.find('input.form-control').autocomplete({
                source: function(request, response) {
                    if(request.term in cache) {
                        response(cache[request.term]);
                        return;
                    }

                    $.getJSON(
                        '/api/v1/search/projects/',
                        request,
                        function(data, status, xhr) {
                            cache[request.term] = data;
                            response(cache[request.term]);
                            return;
                        }
                    );
                },
                minLength: 0,
                select: function(event, ui) {
                    replace_with_selection(ui.item)
                    return false;
                },
                open: function(event, ui) {
                    $(event.target).data('autocomplete-open', true);
                },
                close: function(event, ui) {
                    $(event.target).data('autocomplete-open', false);
                }
            })
        replace_with(input);
        old_elem.val('');

        input.find('.btn-default').on('click', function(e) {
            e.preventDefault();
            var elem = input.find('input.form-control');
            elem.autocomplete( elem.data('autocomplete-open') ? 'close' : 'search' );

        })
    }

    var replace_with_selection = function(project) {
        replace_with(
            $('<div class="panel panel-default autocomplete-selection">' +
                '<div class="panel-heading">' +
                    '<h3 class="panel-title">' +
                        '<span class="pull-right remove-autocomplete-selection">&times;</span>' +
                        project.label +
                    '</h3>' +
                '</div>' +
                '<div class="panel-body">' +
                    project.authors +
                '</div>' +
            '</div>')
        );
        old_elem.val(project.id);
    }

    replace_with_input();

    $('body').on('click', '.remove-autocomplete-selection', function(e) {
        replace_with_input();
    })



});
</script>
</%def>

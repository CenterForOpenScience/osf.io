$(document).ready(function() {
    $("#show-modify-form").click(function() {
        $("#table-view").toggle();
        $("#form-view").toggle();

        var text = $("#show-modify-form").text();
        var new_text = (text.trim() == "Modify Registration Provider") ? "Hide Form" : "Modify Registration Provider";
        $("#show-modify-form").text(new_text);
    });

    $("#discard").click(function(e) {
        e.preventDefault();
        if (window.confirm('Are you sure want to discard all your changes?')) {
            location.reload(true);
        }
    });

    if($('#id_domain_redirect_enabled').checked){
        $('#id_domain').attr('required', "");
    }

    $('#id_domain_redirect_enabled').click(function() {
        if(this.checked) {
            $('#id_domain').attr('required', "");
        }else {
            $('#id_domain').removeAttr('required');

        }
    });

    $("#import-form").submit(function(event) {
        tinymceFields = ['description', 'advisory_board', 'footer_links'];
        checkedBooleanFields = ['domain_redirect_enabled', 'allow_submissions'];
        event.preventDefault();
        $.ajax({
            url: window.templateVars.importUrl,
            type: "post",
            data: new FormData($(this)[0]),
            cache: false,
            contentType: false,
            processData: false,
            success: function(response) {
                for (var field_name in response){
                    if (response.hasOwnProperty(field_name)) {
                        field_value = response[field_name];

                        if (checkedBooleanFields.includes(field_name)) {
                            $("input[name=" + field_name + "]").prop("checked", field_value);
                        } else if (tinymceFields.includes(field_name)) {
                            tinymce.get("id_" + field_name).setContent(field_value);
                        } else if (field_name === "licenses_acceptable") {
                            field_value.forEach(function(element, index, array) {
                                $("input[name=" + field_name + "][value=" + element + "]").prop("checked", true);
                            });
                        } else {
                            var field = $("#id_" + field_name);
                            field.val(field_value);
                        }
                    }
                }
            }
        });
    });

    var getContent = function(taxonomyTextField) {
        currentCustomTaxonomyContent = taxonomyTextField.val();
        if (currentCustomTaxonomyContent === "") {
            currentCustomTaxonomyContent = '{\"include\": [], \"exclude\": [], \"custom\": {}, \"merge\": {}}'
        }
        return JSON.parse(currentCustomTaxonomyContent);
    };

    $( ".taxonomy-action-button" ).click(function() {
        var taxonomyTextField=$("#id_custom_taxonomy_json");
        var content = getContent(taxonomyTextField);
        var value = $("#" + $(this).attr("value")).val();
        var subjects = content[$(this).attr("id")];
        if (subjects.indexOf(value) == -1) {
            subjects.push(value);
        }
        taxonomyTextField.val(JSON.stringify(content, undefined, 4));
    });

    $( "#id-add-custom" ).click(function() {
        var taxonomyTextField=$("#id_custom_taxonomy_json");
        var name = $("#id_custom_name").val();
        var parent = $("#id_custom_parent").val();
        var bepress = $("#id_bepress").val();
        var content = getContent(taxonomyTextField);
        if (content["custom"][name] === undefined) {
            content["custom"][name] = {
                "parent": parent,
                "bepress": bepress
            };
        }

        taxonomyTextField.val(JSON.stringify(content, undefined, 4));
    });


    $( "#id-add-merge" ).click(function() {
        var taxonomyTextField=$("#id_custom_taxonomy_json");
        var merge_from = $("#id_merge_from").val();
        var merge_into = $("#id_merge_into").val();
        var content = getContent(taxonomyTextField);

        if (content["merge"][merge_from] === undefined) {
            content["merge"][merge_from] = merge_into
        }

        taxonomyTextField.val(JSON.stringify(content, undefined, 4));
    });


    $("#id-validate-custom").on("click", function(event) {
       checkTaxonomy();
    });


    function checkTaxonomy() {
        var taxonomyForm = $("#taxonomy-form").serializeArray();
        $.ajax({
            url: window.templateVars.processCustomTaxonomyUrl,
            type: "POST",
            data: taxonomyForm,
            success: function(json) {
                var alert_class_div = (json["feedback_type"] == "success") ? "<div class='alert alert-info'>" : "<div class='alert alert-danger'>";
                $("#taxonomy-field-info").html(alert_class_div + json["message"]+ "</div>");
            }
        });
    };

    $("#show-custom-taxonomy-form").click(function() {
        $("#custom-taxonomy-form").toggle();
    });

    $("#id_include").length && $("#id_include").select2();
    $("#id_exclude").length && $("#id_exclude").select2();
    $("#id_bepress").length && $("#id_bepress").select2();
    $("#id_merge_from").length && $("#id_merge_from").select2();
    $("#id_merge_into").length && $("#id_merge_into").select2();

    $('.subjects-list > li').length &&
    $('.subjects-list > li').click(function() {
        var children_list = 'ul[data-id="' + $(this).data('id') + '"]';
        $(this).parent().find(children_list).toggle();
    });
});

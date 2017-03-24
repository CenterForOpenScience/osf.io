$(document).ready(function() {

    var originalSubjects = window.templateVars.originalSubjects;
    var selected_subjects = originalSubjects.slice();

    var addSubject = function(subject) {
        var subject = parseInt(subject);
        if ($("#id_subjects_chosen").val() !== "") {
            $("#id_subjects_chosen").val($("#id_subjects_chosen").val() + ", " + subject);
        } else {
            $("#id_subjects_chosen").val(subject);
        }

        if (selected_subjects.indexOf(subject) === -1) {
            selected_subjects.push(subject);
        }
    };

    var removeSubject = function(subject) {
        var subjectToRemove = parseInt(subject);
        var re = new RegExp("\\b" + subjectToRemove + "\\b", "g");
        $("#id_subjects_chosen").val($("#id_subjects_chosen").val().replace(re, ""));

        selected_subjects = selected_subjects.filter(function(element) {
            return element !== subjectToRemove;
        });
    };

    var clearSubjects = function() {
        $("#id_subjects_chosen").val("");
        selected_subjects = [];
    };

    // Section and selectors for expanding lists
    $("body").on("click", ".subject-icon", function() {
        var elem = $(this)[0].previousElementSibling.firstChild;
        var nextlevel;

        if ($(this)[0].classList.contains("first-level")) {
            $(".other-levels").hide();
        }

        if (elem.name === "toplevel_subjects") {
            nextlevel = "#secondlevel_subjects"
        } else if (elem.name === "secondlevel_subjects") {
            nextlevel = "#thirdlevel_subjects"
        }
        $.get(window.templateVars.getSubjectsUrl, {"parent_id": elem.value}, function (data) {
            $(nextlevel).html(data["html"]);
        }).then(function(data) {
            for (i = 0; i < data["subject_ids"].length; i++) {
                if (selected_subjects.indexOf(data["subject_ids"][i]) !== -1) {
                    $("input[value=" + data["subject_ids"][i] + "]").prop("checked", true);
                }
            }
        });
    });

    // Section for adding and removing checked items
    $("body").on("click", "input[type='checkbox']", function() {
        var subjectsToRemove = [];
        var elem = $(this);
        if (elem.prop('checked') && elem.prop("name") !== "licenses_acceptable") {
            addSubject(elem[0].value);

            // Also make sure to select parents and grandparents!
            var parentId = elem[0].getAttribute("parent");
            if (parentId) {
                addSubject(parentId);
                var parentElem = $("input[value=" + parentId + "]");
                if (parentElem.prop("name") !== "licenses_acceptable") {
                    parentElem.prop("checked", true);
                    grandparentId = parentElem[0].getAttribute("parent");
                    if (grandparentId) {
                        addSubject(grandparentId);
                        grandparentElem = $("input[value=" + grandparentId + "]");
                        if (grandparentElem.prop("name") !== "licenses_acceptable") {
                            grandparentElem.prop("checked", true);
                        }
                    }
                }
            }
        } else {
            $.get(
                window.templateVars.getDescendantsUrl,
                {"parent_id": elem[0].value}
            ).then(function(data) {
                var descendants = data["all_descendants"];
                for (j=0; j < descendants.length; j++) {
                    var input = $("input[value=" + descendants[j] + "]");

                    if (input.prop("name") !== "licenses_acceptable") {
                        input.prop("checked", false);
                    }
                    var descendant_index = selected_subjects.indexOf(parseInt(descendants[j]));
                    if (descendant_index > -1) {
                        subjectsToRemove.push(descendants[j]);
                    }
                }
            }).then(function() {
                subjectsToRemove.push(elem[0].value);
                for (i=0; i<subjectsToRemove.length; i++) {
                    removeSubject(subjectsToRemove[i]);
                }

            });
        }
    });

    $("#show-modify-form").click(function() {

        $("#table-view").toggle();
        $("#form-view").toggle();

        var text = $("#show-modify-form").text();
        var new_text = (text.trim() == "Modify Preprint Provider") ? "Hide Form" : "Modify Preprint Provider";
        $("#show-modify-form").text(new_text);
    });

    var populateSubjects = function(rules) {
        $.get(window.templateVars.rulesToSubjectsUrl, {"rules": JSON.stringify(rules)}, function (data) {
            var subjects = data["subjects"];
            for (var h=0; h<selected_subjects.length; h++) {
                $("input[value=" + selected_subjects[h] + "]").prop("checked", false);
            }
            clearSubjects();
            for (var i=0; i<subjects.length; i++) {
                addSubject(subjects[i]);
                $("input[value=" + subjects[i] + "]").prop("checked", true);
            }
        });
    };

    $("#import-form").submit(function(event) {
        event.preventDefault();
        $.ajax({
            url: window.templateVars.importUrl,
            type: "post",
            data: new FormData($(this)[0]),
            cache: false,
            contentType: false,
            processData: false,
            success: function(response) {
                for (var k in response){
                    if (response.hasOwnProperty(k)) {
                        if (k === "subjects_acceptable") {
                            populateSubjects(response[k]);
                        } else {
                            var field = $("#id_" + k);
                            field.val(response[k]);
                        }
                    }
                }
            }
        });
    });
});

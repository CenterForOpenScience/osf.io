<div id="registrationEditorScope">
    <div class="container">
        <div class="row">
            <div class="span8 col-md-2 columns eight large-8">
                <ul class="nav nav-stacked list-group" data-bind="foreach: {data: currentPages, as: 'page'}">
                    <li class="re-navbar">
                        <a class="registration-editor-page" id="top-nav" style="text-align: left; font-weight:bold;" data-bind="text: title, click: $root.selectPage">
                            <i class="fa fa-caret-right"></i>
                        </a>
                        <span class="btn-group-vertical" role="group">
                  <ul class="list-group" data-bind="foreach: {data: Object.keys(page.questions), as: 'qid'}">
                    <span data-bind="with: page.questions[qid]">
                      <li data-bind="css: {
                                       registration-editor-question-current: $root.currentQuestion().id === $data.id
                                     },
                                     click: $root.currentQuestion.bind($root, $data)"
                          class="registration-editor-question list-group-item">
                        <a data-bind="attr.href: '#' + id, text: nav "></a><span class="pull-right" data-bind="text: $root.getUnseenComments($root.currentQuestion)"></span>
                    </li>
                    </span>
                </ul>
                </span>
                </li>
                </ul>
            </div>
            <div class="span8 col-md-9 columns eight large-8">
                <a data-bind="click: previousPage" style="padding-left: 5px;">
                    <i style="display:inline-block; padding-left: 5px; padding-right: 5px;" class="fa fa-arrow-left"></i>Previous
                </a>
                <a data-bind="click: nextPage" style="float:right; padding-right:5px;">Next
                    <i style="display:inline-block; padding-right: 5px; padding-left: 5px;" class="fa fa-arrow-right"></i>
                </a>
                <!-- EDITOR -->
                <div data-bind="if: currentQuestion">
                    <div id="registrationEditor" data-bind="template: {data: currentQuestion, name: 'editor'}">
                    </div>
                </div>
                <p>Last saved: <span data-bind="text: $root.lastSaved()"></span>
                </p>
                <button data-bind="click: save" type="button" class="btn btn-success">Save
                </button>
            </div>
        </div>
    </div>
</div>
<script id="preSubmission" type="text/html">
	<p>You are about to submit your study and analysis for review. This will notify Prereg Prize Administrators who will begin to review it.
		You will still be able to edit this registration but must submit again. Are you sure you are ready for review?
	</p>
</script>
<script id="postSubmission" type="text/html">
	<img src="https://i.imgur.com/0aCtj3b.png"><br>
	<p>You have successfully submitted your study and analysis plans. The plans are not yet fully registered.
	Next, staff from the Center for Open Science will have the plans reviewed to assure that enough detail was included.
	Reviewers may accept your plans or request revisions. Remember, in order to be eligible for the prize, your plans must be accepted
	through this review process. We will contact you within five business days with a status update.
	If you have any questions, please contact <a href="mailto:prereg@cos.io">prereg@cos.io</a> and we will be happy to help you.</p>
</script>

<%include file="registration_editor_templates.mako" />

<div id="commentPane">

    <div class="cp-handle">
        <i class="icon-comments-alt icon-white icon-2x comment-handle-icon" style=""></i>
    </div>

    <div class="cp-bar"></div>

    <div id="comments" class="cp-sidebar">

        <h4>Discussion</h4>
        <div data-bind="foreach: {data: discussion, afterAdd: setupToolTips}">
            <a data-toggle="tooltip" data-bind="attr: {href: url, title: fullname}">
                <img data-bind="attr: {src: gravatarUrl}"/>
            </a>
        </div>

        <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>
        <div data-bind="if: canComment" style="margin-top: 20px">

            <form class="form">
                <div class="form-group">
                    <textarea class="form-control" placeholder="Add a comment" data-bind="value: replyContent, valueUpdate: 'input'"></textarea>
                </div>
                <div data-bind="if: replyNotEmpty" class="form-inline">
                    <select class="form-control" data-bind="options: privacyOptions, optionsText: privacyLabel, value: replyPublic"></select>
                    <a class="btn btn-default btn-default" data-bind="click: submitReply"><i class="icon-check"></i> Save</a>
                    <a class="btn btn-default btn-default" data-bind="click: cancelReply"><i class="icon-undo"></i> Cancel</a>
                    <a data-bind="text: replyErrorMessage" class="comment-error"></a>
                </div>
            </form>
        </div>
    </div>

</div>

<script type="text/html" id="commentTemplate">

    <div class="comment-container">

        <div class="comment-body">

            <div data-bind="if: isDeleted">
                <div>
                    <span data-bind="if: hasChildren">
                        <i data-bind="css: toggleIcon, click: toggle"></i>
                    </span>
                    Comment deleted
                </div>
                <div data-bind="if: canEdit">
                    <a data-bind="click: startUndelete">Restore</a>
                    <div data-bind="if: undeleting">
                        <a class="btn btn-default btn-sm" data-bind="click: submitUndelete">Submit</a>
                        <a class="btn btn-default btn-sm" data-bind="click: cancelUndelete">Cancel</a>
                    </div>
                </div>
            </div>

            <div data-bind="if: isAbuse">
                <div>
                    <span data-bind="if: hasChildren">
                        <i data-bind="css: toggleIcon, click: toggle"></i>
                    </span>
                    Comment reported
                </div>
                <a data-bind="click: startUnreportAbuse">Not abuse</a>
                <div data-bind="if: unreporting">
                    <a class="btn btn-default btn-sm" data-bind="click: submitUnreportAbuse">Submit</a>
                    <a class="btn btn-default btn-sm" data-bind="click: cancelUnreportAbuse">Cancel</a>
                </div>
            </div>

            <div data-bind="if: isVisible">

                <div class="comment-info">
                    <form class="form-inline">
                        <img data-bind="attr: {src: author.gravatarUrl}"/>
                        <a class="comment-author" data-bind="text: author.name, attr: {href: author.url}"></a>
                        <span class="comment-date pull-right">
                            <span data-bind="template: {if: modified, afterRender: setupToolTips}">
                                <a data-toggle="tooltip" data-bind="attr: {title: prettyDateModified()}">*</a>
                            </span>
                            <span data-bind="text: prettyDateCreated"></span>
                        </span>
                    </form>
                </div>

                <div>

                    <div class="comment-content">

                        <div data-bind="ifnot: editing">
                            <span data-bind="if: hasChildren">
                                <i data-bind="css: toggleIcon, click: toggle"></i>
                            </span>
                            <span data-bind="text: content, css: {'edit-comment': editHighlight}, event: {mouseenter: startHoverContent, mouseleave: stopHoverContent, click: edit}"></span>
                        </div>

                        <!--
                            Hack: Use template binding with if rather than vanilla if
                            binding to get access to afterRender
                        -->
                        <div data-bind="template {if: editing, afterRender: autosizeText}">
                            <div class="form-group" style="padding-top: 10px">
                                <textarea class="form-control" data-bind="value: content"></textarea>
                            </div>
                            <div class="form-inline">
                                <select class="form-control" data-bind="options: privacyOptions, optionsText: privacyLabel, value: isPublic"></select>
                                <a class="btn btn-default btn-default" data-bind="click: submitEdit"><i class="icon-check"></i> Save</a>
                                <a class="btn btn-default btn-default" data-bind="click: cancelEdit"><i class="icon-undo"></i> Cancel</a>
                                <span data-bind="text: editErrorMessage" class="comment-error"></span>
                            </div>
                        </div>

                    </div>

                    <div class="comment-actions">
                        <span data-bind="ifnot: editing">
                            <!-- ko if: showPrivate -->
                                <span data-bind="click: togglePrivacy" class="label label-danger" style="cursor: pointer">Private</span>
                            <!-- /ko -->
                            <!-- ko ifnot: showPrivate -->
                                <span data-bind="click: togglePrivacy" class="label label-success" style="cursor: pointer">Public</span>
                            <!-- /ko -->
                        </span>
                        <!-- Action bar -->
                        <div data-bind="ifnot: editing" class="comment-actions pull-right">
                            <span data-bind="if: $root.canComment, click: showReply">
                                <i class="icon-reply"></i>
                            </span>
                            <span data-bind="if: canReport, click: reportAbuse">
                                <i class="icon-warning-sign"></i>
                            </span>
                            <span data-bind="if: canEdit, click: startDelete">
                                <i class="icon-trash"></i>
                            </span>

                        </div>

                    </div>

                    <div class="comment-report" data-bind="if: reporting">
                        <form class="form-inline">
                            <select class="form-control" data-bind="options: abuseOptions, optionsText: abuseLabel, value: abuseCategory"></select>
                            <input class="form-control" data-bind="value: abuseText" placeholder="Describe abuse" />
                        </form>
                        <a class="btn btn-default btn-sm" data-bind="click: submitAbuse"><i class="icon-check"></i> Report</a>
                        <a class="btn btn-default btn-sm" data-bind="click: cancelAbuse"><i class="icon-undo"></i> Cancel</a>
                    </div>

                    <div class="comment-delete" data-bind="if: deleting">
                        <a class="btn btn-default btn-sm" data-bind="click: submitDelete"><i class="icon-check"></i> Delete</a>
                        <a class="btn btn-default btn-sm" data-bind="click: cancelDelete"><i class="icon-undo"></i> Cancel</a>
                    </div>

                </div>

            </div>


        </div>

        <ul class="comment-list">

            <!-- ko if: showChildren -->
                <!-- ko template: {name:  'commentTemplate', foreach: comments} -->
                <!-- /ko -->
            <!-- /ko -->

            <!-- ko if: replying -->

                <div>
                    <div class="form-group" style="padding-top: 10px">
                        <textarea class="form-control" placeholder="Add a comment" data-bind="value: replyContent"></textarea>
                    </div>
                    <div class="form-inline">
                        <select class="form-control" data-bind="options: privacyOptions, optionsText: privacyLabel, value: replyPublic"></select>
                        <a class="btn btn-default btn-default" data-bind="click: submitReply"><i class="icon-check"></i> Save</a>
                        <a class="btn btn-default btn-default" data-bind="click: cancelReply"><i class="icon-undo"></i> Cancel</a>
                        <span data-bind="text: replyErrorMessage" class="comment-error"></span>
                    </div>
                </div>

            <!-- /ko -->

        </ul>

    </div>

</script>

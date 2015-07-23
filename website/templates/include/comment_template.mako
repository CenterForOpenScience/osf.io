<div class="scripted" id="commentPane">

    <div class="cp-handle" data-bind="click:removeCount">
        <p data-bind="text: displayCount" class="unread-comments-count"></p>
        <i class="fa fa-comments-o fa-inverse fa-2x comment-handle-icon" style=""></i>
    </div>
    <div class="cp-bar"></div>

    <div id="comments" class="cp-sidebar bg-color-light">
        <h4>
            <span>${node['title']} Discussion</span>
            <span data-bind="foreach: {data: discussion, afterAdd: setupToolTips}" class="pull-right">
                <a data-toggle="tooltip" data-bind="attr: {href: url, title: fullname}" data-placement="bottom">
                    <img data-bind="attr: {src: gravatarUrl}"/>
                </a>
            </span>
        </h4>

        <div data-bind="if: canComment" style="margin-top: 20px">
            <form class="form">
                <div class="form-group">
                    <textarea class="form-control" placeholder="Add a comment" data-bind="value: replyContent, valueUpdate: 'input', attr: {maxlength: $root.MAXLENGTH}"></textarea>
                </div>
                <div class="clearfix">
                    <div data-bind="if: replyNotEmpty" class="form-inline pull-right">
                        <a class="btn btn-default btn-sm" data-bind="click: cancelReply, css: {disabled: submittingReply}"> Cancel</a>
                        <a class="btn btn-success btn-sm" data-bind="click: submitReply, css: {disabled: submittingReply}"> {{commentButtonText}}</a>
                        <span data-bind="text: replyErrorMessage" class="comment-error"></span>
                    </div>
                </div>
                <div class="comment-error">{{errorMessage}}</div>
            </form>
        </div>

        <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>

    </div>

</div>

<script type="text/html" id="commentTemplate">
    <div class="comment-container" data-bind="if: shouldShow">

        <div class="comment-body m-b-sm p-sm osf-box">
            <div data-bind="if: isDeleted">
                <div>
                    <span data-bind="if: hasChildren">
                        <i data-bind="css: toggleIcon, click: toggle"></i>
                    </span>
                    Comment deleted
                </div>
                <div data-bind="if: canEdit">
                    <a data-bind="click: startUndelete">Restore</a>
                    <div class="clearfix" data-bind="if: undeleting">
                        <div class="pull-right">
                            <a class="btn btn-default btn-sm" data-bind="click: cancelUndelete">Cancel</a>
                            <a class="btn btn-success btn-sm" data-bind="click: submitUndelete">Save</a>
                        </div>
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
                <div class="clearfix" data-bind="if: unreporting">
                    <div class="pull-right">
                    <a class="btn btn-default btn-sm" data-bind="click: cancelUnreportAbuse">Cancel</a>
                    <a class="btn btn-success btn-sm" data-bind="click: submitUnreportAbuse">Save</a>
                    </div>
                </div>
            </div>

            <div data-bind="if: isVisible">

                <div class="comment-info">
                    <form class="form-inline">
                        <img data-bind="attr: {src: author.gravatarUrl}"/>
                        <span data-bind="if: author.id">
                            <a class="comment-author" data-bind="text: author.name, attr: {href: author.url}"></a>
                        </span>
                        <span data-bind="ifnot: author.id">
                            <span class="comment-author" data-bind="text: author.name"></span>
                        </span>
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
                            <span class="component-overflow"
                              data-bind="html: contentDisplay, css: {'edit-comment': editHighlight}, event: {mouseenter: startHoverContent, mouseleave: stopHoverContent}"></span>
                            <span class="pull-right" data-bind="if: hasChildren">
                                <i data-bind="css: toggleIcon, click: toggle"></i>
                            </span>
                        </div>

                        <!--
                            Hack: Use template binding with if rather than vanilla if
                            binding to get access to afterRender
                        -->
                        <div data-bind="template {if: editing, afterRender: autosizeText}">
                            <div class="form-group" style="padding-top: 10px">
                                <textarea class="form-control" data-bind="value: content, valueUpdate: 'input', attr: {maxlength: $root.MAXLENGTH}"></textarea>
                            </div>
                            <div class="clearfix">
                                <div class="form-inline pull-right">
                                    <a class="btn btn-default btn-sm" data-bind="click: cancelEdit">Cancel</a>
                                    <a class="btn btn-success btn-sm" data-bind="click: submitEdit, visible: editNotEmpty">Save</a>
                                    <span data-bind="text: editErrorMessage" class="comment-error"></span>
                                </div>
                            </div>
                        </div>

                    </div>

                    <div>

                        <span class="comment-error">{{errorMessage}}</span>

                        <span>&nbsp;</span>

                        <!-- Action bar -->
                        <div data-bind="ifnot: editing" class="comment-actions pull-right">
                            <span data-bind="if: canEdit, click: edit">
                                <i class="fa fa-pencil"></i>
                            </span>
                            <span data-bind="if: $root.canComment, click: showReply">
                                <i class="fa fa-reply"></i>
                            </span>
                            <span data-bind="if: canReport, click: reportAbuse">
                                <i class="fa fa-warning"></i>
                            </span>
                            <span data-bind="if: canEdit, click: startDelete">
                                <i class="fa fa-trash-o"></i>
                            </span>

                        </div>

                    </div>

                    <div class="comment-report clearfix" data-bind="if: reporting">
                        <form class="form-inline">
                            <select class="form-control" data-bind="options: abuseOptions, optionsText: abuseLabel, value: abuseCategory"></select>
                            <input class="form-control" data-bind="value: abuseText" placeholder="Describe abuse" />
                        </form>
                        <div class="pull-right m-t-xs">
                            <a class="btn btn-default btn-sm" data-bind="click: cancelAbuse"> Cancel</a>
                            <a class="btn btn-danger btn-sm" data-bind="click: submitAbuse"> Report</a>
                        </div>
                    </div>

                    <div class="comment-delete clearfix m-t-xs" data-bind="if: deleting">
                        <div class="pull-right">
                            <a class="btn btn-default btn-sm" data-bind="click: cancelDelete">Cancel</a>
                            <a class="btn btn-danger btn-sm" data-bind="click: submitDelete">Delete</a>
                        </div>
                    </div>

                </div>

            </div>


        </div>

        <ul class="comment-list">

            <!-- ko if: replying -->

                <div>
                    <div class="form-group" style="padding-top: 10px">
                        <textarea class="form-control" placeholder="Add a comment" data-bind="value: replyContent, valueUpdate: 'input', attr: {maxlength: $root.MAXLENGTH}"></textarea>
                    </div>
                    <div class="clearfix">
                        <div class="pull-right">
                            <a class="btn btn-default btn-sm" data-bind="click: cancelReply, css: {disabled: submittingReply}"> Cancel</a>
                            <a class="btn btn-success btn-sm" data-bind="click: submitReply, visible: replyNotEmpty, css: {disabled: submittingReply}"> {{commentButtonText}}</a>
                            <span data-bind="text: replyErrorMessage" class="comment-error"></span>
                        </div>
                    </div>
                </div>

            <!-- /ko -->

            <!-- ko if: showChildren -->
                <!-- ko template: {name:  'commentTemplate', foreach: comments} -->
                <!-- /ko -->
            <!-- /ko -->

        </ul>

    </div>

</script>


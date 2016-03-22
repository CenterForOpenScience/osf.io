<div class="scripted comment-pane">

    <div class="cp-handle-div cp-handle pull-right pointer hidden-xs" data-bind="click:removeCount" data-toggle="tooltip" data-placement="bottom" title="Comments">
        <span data-bind="if: unreadComments() !== 0">
            <span data-bind="text: displayCount" class="badge unread-comments-count"></span>
        </span>
        <i class="fa fa-comments-o fa-2x comment-handle-icon"></i>
    </div>
    <div class="cp-bar"></div>


    <div class="comments cp-sidebar">
        <div class="cp-sidebar-content">
            <button type="button" class="close text-smaller" data-bind="click: togglePane">
                <i class="fa fa-times"></i>
            </button>
            <h4>
                <span data-bind="if: page() == 'files'">Files | <span data-bind="text: pageTitle"></span> Discussion</span>
                <span data-bind="if: page() == 'wiki'">Wiki | <span data-bind="text: pageTitle"></span> Discussion</span>
                <span data-bind="if: page() == 'node'"><span data-bind="text: pageTitle"></span> | Discussion</span>
            </h4>

            <div data-bind="if: canComment" style="margin-top: 20px">
                <form class="form">
                    <div class="form-group">
                        <span>
                            <textarea class="form-control atwho-input" placeholder="Add a comment" data-bind="value: replyContent, valueUpdate: 'input', attr: {maxlength: $root.MAXLENGTH}"></textarea>
                        </span>
                    </div>
                    <div data-bind="if: replyNotEmpty" class="form-group">
                        <div class="clearfix">
                            <div class="pull-right">
                                <a class="btn btn-default btn-sm" data-bind="click: cancelReply, css: {disabled: submittingReply}">Cancel</a>
                                <a class="btn btn-success btn-sm" data-bind="click: submitReply, css: {disabled: submittingReply}, text: commentButtonText"></a>
                                <span data-bind="text: replyErrorMessage" class="text-danger"></span>
                            </div>
                        </div>
                    </div>
                    <div class="text-danger" data-bind="text: errorMessage"></div>
                </form>
            </div>
            <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>
            <!-- ko if: loadingComments -->
            <div style="text-align: center;">
                <div class="logo-spin logo-lg"></div>
            </div>
            <!-- /ko -->
        </div>
    </div>

</div>
<%include file="comment_template.mako" />

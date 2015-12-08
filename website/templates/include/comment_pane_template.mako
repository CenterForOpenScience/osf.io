<div class="scripted comment-pane hidden-xs">

    <div class="cp-handle pull-right pointer" data-bind="click:removeCount" data-toggle="tooltip" data-placement="bottom" title="Discussion Pane">
        <span data-bind="if: unreadComments() !== 0">
            <span data-bind="text: displayCount" class="badge unread-comments-count"></span>
        </span>
        <i class="fa fa-comments-o fa-2x comment-handle-icon"></i>
    </div>
    <div class="cp-bar"></div>


    <div class="comments cp-sidebar">
        <h4>
            <span data-bind="if: page() == 'node' ">${node['title']} Discussion</span>
            %if file_name:
                <span data-bind="if: page() == 'files'">Files | ${file_name} Discussion</span>
            %endif
        </h4>

        <div data-bind="if: canComment" style="margin-top: 20px">
            <form class="form">
                <div class="form-group">
                    <span data-bind="if:commented">
                        <textarea class="form-control" placeholder="Add a comment" data-bind="value: replyContent, valueUpdate: 'input', attr: {maxlength: $root.MAXLENGTH}"></textarea>
                    </span>
                    <span data-bind="ifnot:commented">
                        <textarea class="form-control" placeholder="Add the first comment on this page!" data-bind="value: replyContent, valueUpdate: 'input', attr: {maxlength: $root.MAXLENGTH}"></textarea>
                    </span>
                </div>
                <div data-bind="if: replyNotEmpty" class="form-group">
                    <div class="clearfix">
                        <div class="pull-right">
                            <a class="btn btn-default btn-sm" data-bind="click: cancelReply, css: {disabled: submittingReply}">Cancel</a>
                            <a class="btn btn-success btn-sm" data-bind="click: submitReply, css: {disabled: submittingReply}">{{commentButtonText}}</a>
                            <span data-bind="text: replyErrorMessage" class="text-danger"></span>
                        </div>
                    </div>
                </div>
                <div class="text-danger">{{errorMessage}}</div>
            </form>
        </div>

        <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>

    </div>

</div>
<%include file="comment_template.mako" />

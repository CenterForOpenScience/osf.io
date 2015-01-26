<div class="commentPane hidden-xs">

    <div class="cp-handle pull-right" data-bind="click:removeCount" data-toggle="tooltip" data-placement="bottom" title="Discussion Pane">
        <span data-bind="if: unreadComments() !== 0">
            <span data-bind="text: displayCount" class="badge unread-comments-count"></span>
        </span>
        <i class="icon-comments-alt icon-3x comment-handle-icon" style="color: #428bca"></i>
    </div>
    <div class="cp-bar"></div>


    <div class="comments cp-sidebar">
        <h4>
            <span data-bind="if: page() == 'node' ">${node['title']} Discussion</span>
            <span data-bind="if: page() == 'wiki' ">Wiki
               <span data-bind="if: id().toLowerCase() != 'home' "><span data-bind="text: '- ' + id() + ' '"></span></span>
                Discussion
            </span>
            % if not file_name is UNDEFINED:
                <span data-bind="if: page() == 'files'">Files | ${file_name} Discussion</span>
            % endif
        </h4>

        <div data-bind="if: commented">
            Show <a data-bind="click: showRecent">recently commented users</a> or
            <a data-bind="click: showFrequent">most frequently commented users</a>
            <div style="padding-bottom: 10px">
                <span class="pull-right" data-bind="foreach: {data: discussion, afterAdd: setupToolTips}">
                    <a data-toggle="tooltip" data-bind="attr: {href: url, title: fullname}" data-placement="bottom">
                        <img data-bind="attr: {src: gravatarUrl}"/>
                    </a>
                </span>
            </div>
        </div>

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
                <div data-bind="if: replyNotEmpty" class="form-inline">
                    <a class="btn btn-primary" data-bind="click: submitReply, css: {disabled: submittingReply}"><i class="icon-check"></i> {{saveButtonText}}</a>
                    <a class="btn btn-default" data-bind="click: cancelReply, css: {disabled: submittingReply}"><i class="icon-undo"></i> Cancel</a>
                    <span data-bind="text: replyErrorMessage" class="comment-error"></span>
                </div>
                <div class="comment-error">{{errorMessage}}</div>
            </form>
        </div>

        <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>

    </div>

</div>
<%include file="comment_template.mako" />

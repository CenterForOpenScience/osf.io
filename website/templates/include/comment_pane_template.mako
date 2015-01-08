<div class="commentPane">

    <div class="cp-handle" data-bind="click:removeCount">
        <p data-bind="text: displayCount" class="unread-comments-count"></p>
        <i class="icon-comments-alt icon-white icon-2x comment-handle-icon" style=""></i>
    </div>
    <div class="cp-bar"></div>

    <div class="comments cp-sidebar">
        <h4>
            <span data-bind="if: page() =='node' ">${node['title']} {{title}}Discussion</span>
            <span data-bind="if: page() =='wiki' ">Wiki
               <span data-bind="if: id().toLowerCase() != 'home' "><span data-bind="text: '- ' + id() + ' '"></span></span>
                Discussion
            </span>
        </h4>

        <div data-bind="visible: discussion().length > 0">
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
                    <a class="btn btn-default btn-default" data-bind="click: submitReply, css: {disabled: submittingReply}"><i class="icon-check"></i> {{saveButtonText}}</a>
                    <a class="btn btn-default btn-default" data-bind="click: cancelReply, css: {disabled: submittingReply}"><i class="icon-undo"></i> Cancel</a>
                    <span data-bind="text: replyErrorMessage" class="comment-error"></span>
                </div>
                <div class="comment-error">{{errorMessage}}</div>
            </form>
        </div>

        <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>

    </div>

</div>
<%include file="comment_template.mako" />

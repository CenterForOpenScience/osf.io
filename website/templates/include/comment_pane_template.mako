<div class="scripted comment-pane">

    <div class="cp-handle-div cp-handle pull-right pointer hidden-xs" data-bind="click:removeCount" data-toggle="tooltip" data-placement="bottom" title="Comments">
        <span data-bind="if: unreadComments() !== 0">
            <span data-bind="text: displayCount" class="badge unread-comments-count"></span>
        </span>
        <i class="fa fa-comments-o fa-2x comment-handle-icon"></i>
    </div>
    <div class="cp-bar"></div>


    <div class="comments cp-sidebar" id="comments_window">
        <div class="cp-sidebar-content">
            <button type="button" class="close text-smaller" data-bind="click: togglePane">
                <i class="fa fa-times"></i>
            </button>
            <h4 style="margin-bottom: 20px">
                <span data-bind="if: page() == 'files'">Files | <span data-bind="text: pageTitle"></span> Discussion</span>
                <span data-bind="if: page() == 'wiki'">Wiki | <span data-bind="text: pageTitle"></span> Discussion</span>
                <span data-bind="if: page() == 'node'"><span data-bind="text: pageTitle"></span> | Discussion</span>
            </h4>

            ## Discourse comment embedding
            <div id='discourse-comments' data-discourse-url='${ discourse_url }' data-discourse-topic-id='${ discourse_topic_id }'></div>
        </div>
    </div>

</div>

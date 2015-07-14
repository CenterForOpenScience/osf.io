<div class="row" data-bind="attr: {id: $index}, event: {mouseover: highlightRow, mouseout: unhighlightRow, click: goToDraft}">
    <div data-bind="text: $data.registration_metadata.q1.value" class="col-md-1" id="submission_title"></div>
    <div data-bind="text: $data.initiator.fullname" class="col-md-1" id="name"></div>
    <div data-bind="text: $data.initiator.username" class="col-md-1" id="email"></div>
    <div data-bind="text: formatTime($data.initiated)" class="col-md-1" id="begun"></div>
    <div data-bind="text: formatTime($data.updated)" class="col-md-1" id="submitted"></div>
    <div  class="col-md-1" id="comments_sent">
        <span data-bind="text: 'no'"></span><i data-bind="click: selectValue, clickBubble: false, event: {mouseover: enlargeIcon, mouseout: shrinkIcon}" style="margin-left: 10px" class="fa fa-pencil"></i>
    </div>
    <div data-bind="text: 'no'" class="col-md-1" id="new_comments"></div>
    <div data-bind="text: 'no'" class="col-md-1" id="approved"></div>
    <div data-bind="text: 'no'" class="col-md-1" id="registered"></div>
    <div class="col-md-1" id="proof_of_pub">
        <span data-bind="text: 'no'"></span><i data-bind="click: selectValue, clickBubble: false, event: {mouseover: enlargeIcon, mouseout: shrinkIcon}" style="margin-left: 10px" class="fa fa-pencil"></i>
    </div>
    <div class="col-md-1" id="payment_sent">
        <span data-bind="text: 'no'"></span><i data-bind="click: selectValue, clickBubble: false, event: {mouseover: enlargeIcon, mouseout: shrinkIcon}" style="margin-left: 10px" class="fa fa-pencil"></i>
    </div>
    <div class="col-md-1" id="notes">
        <span data-bind="text: 'none'"></span><i data-bind="click: addNotes, clickBubble: false, event: {mouseover: enlargeIcon, mouseout: shrinkIcon}" style="margin-left: 10px" class="fa fa-pencil"></i>
    </div>
</div>

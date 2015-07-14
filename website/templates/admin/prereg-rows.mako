<div class="row" data-bind="attr: {id: $index}, event: {mouseover: $parent.highlightRow, mouseout: $parent.unhighlightRow, click: $parent.goToDraft}">
    <div data-bind="text: $data.registration_metadata.q1.value" class="col-md-1" id="submission_title"></div>
    <div data-bind="text: $data.initiator.fullname" class="col-md-1" id="name"></div>
    <div data-bind="text: $data.initiator.username" class="col-md-1" id="email"></div>
    <div data-bind="text: $parent.formatTime($data.initiated)" class="col-md-1" id="begun"></div>
    <div data-bind="text: $parent.formatTime($data.updated)" class="col-md-1" id="submitted"></div>
    <div  class="col-md-1" id="comments_sent">
        <span data-bind="text: $parent.commentsSent"></span><i data-bind="click: $parent.selectValue, clickBubble: false, event: {mouseover: $parent.enlargeIcon, mouseout: $parent.shrinkIcon}" style="margin-left: 10px" class="fa fa-pencil"></i>
    </div>
    <div data-bind="text: 'no'" class="col-md-1" id="new_comments"></div>
    <div data-bind="text: 'no'" class="col-md-1" id="approved"></div>
    <div data-bind="text: 'no'" class="col-md-1" id="registered"></div>
    <div class="col-md-1" id="proof_of_pub">
        <span data-bind="text: $parent.proofOfPub, attr: {class: 'proof_of_pub' + $index()}"></span><i data-bind="click: $parent.editItem.bind($data, 'proof_of_pub' + $index()), clickBubble: false, event: {mouseover: $parent.enlargeIcon, mouseout: $parent.shrinkIcon}, attr: {class: 'proof_of_pub' + $index() + ' fa fa-pencil'}" style="margin-left: 10px"></i>
        <div data-bind="attr: {class: 'input_proof_of_pub' + $index()}, valueUpdate: 'afterkeydown', enterkey: $parent.stopEditing.bind($data, 'proof_of_pub' + $index())" style="display: none">
            <div><input type="radio" data-bind="value: 'no', attr: {class: 'input_proof_of_pub' + $index()}, checked: $parent.proofOfPub"/>No</div>
            <div><input type="radio" data-bind="value: 'yes', attr: {class: 'input_proof_of_pub' + $index()}"/>Yes</div>
        </div>
    </div>
    <div class="col-md-1" id="payment_sent">
        <span data-bind="text: $parent.paymentSent"></span><i data-bind="click: $parent.selectValue, clickBubble: false, event: {mouseover: $parent.enlargeIcon, mouseout: $parent.shrinkIcon}" style="margin-left: 10px" class="fa fa-pencil"></i>
    </div>
    <div class="col-md-1" id="notes">
        <span data-bind="text: $parent.notes"></span><i data-bind="click: $parent.addNotes, clickBubble: false, event: {mouseover: $parent.enlargeIcon, mouseout: $parent.shrinkIcon}" style="margin-left: 10px" class="fa fa-pencil"></i>
    </div>
</div>


<span>Page: <span id="pageNum"></span> / <span id="pageCount"></span></span><br>

<div>
    <nobr>

        <button unselectable="on" id="previousButton" class="mfr-pdf-button">
            <img id="leftArrow" src="/static/mfr/pdf/images/leftarrow.png" style="width: 25px">
        </button>

        <canvas id="the-canvas" style="border:1px solid black"></canvas>

        <button unselectable="on" id="nextButton" class="mfr-pdf-button">
            <img id="rightArrow" src="/static/mfr/pdf/images/rightarrow.png" style="width: 25px;">
        </button>

    </nobr>
</div>


<script type="text/javascript" src="${STATIC_PATH}/pdf/js/pdf.min.js"></script>
<script type="text/javascript" src="${STATIC_PATH}/pdf/js/compatibility.js"></script>
<script type="text/javascript">
    // TODO: Figure out why we have to do this

(function(){
    PDFJS.workerSrc = '${STATIC_PATH}/pdf/js/pdf.worker.js';
    var url = "${url}";
    PDFJS.disableWorker = true;
    var pdfDoc = null,
        pageNum = 1,
        scale = 1.25,
        canvas = document.getElementById('the-canvas'),
        ctx = canvas.getContext('2d');

    //
    // Get page info from document, resize canvas accordingly, and render page
    //

    var $prevButton = $('#previousButton');
    var $nextButton = $("#nextButton");
    var $rightArrow = $("#rightArrow");
    var $leftArrow = $("#leftArrow");

    function renderPage(num) {
        // Using promise to fetch the page

        pdfDoc.getPage(num).then(function(page) {
            var viewport = page.getViewport(scale);
            canvas.height = viewport.height;
            canvas.width = viewport.width;


            // Render PDF page into canvas context
            var renderContext = {
                canvasContext: ctx,
                viewport: viewport
            };

            var navBarHeight = viewport.height + 2 + "px";

            $prevButton.css("height", navBarHeight);
            $nextButton.css("height",navBarHeight);

            page.render(renderContext);
      });

      // Update page counters
      document.getElementById('pageNum').textContent = pageNum;
      document.getElementById('pageCount').textContent = pdfDoc.numPages;
    }

    //
    // Go to previous page
    //

    function goPrevious() {
        if (pageNum <= 1)
            return;
        pageNum--;
        renderPage(pageNum);
    }

    $("#previousButton").click(function(){
        goPrevious()
        var nextButton = this;
        nextButton.disabled = true;
        setTimeout(function(){
            nextButton.disabled = false
        }, 1000);
    });

    $prevButton.mouseout(function(){
        $( this ).removeClass("active");
    })
    .mouseup(function() {
        $( this ).removeClass("active");
    })
    .mousedown(function() {
        $( this ).addClass("active");
    });


    //
    // Go to next page
    //

    function goNext() {
        if (pageNum >= pdfDoc.numPages)
            return;
        pageNum++;
        renderPage(pageNum);
    }

    $("#nextButton").click(function(){
        goNext()
        var nextButton = this;
        nextButton.disabled = true;
        setTimeout(function(){
            nextButton.disabled = false
        }, 1000);
    });

    $nextButton.mouseout(function(){
        $( this ).removeClass("active");
    })
    .mouseup(function() {
        $( this ).removeClass("active");
    })
    .mousedown(function() {
        $( this ).addClass("active");
    });

    PDFJS.getDocument(url).then(function getPdf(_pdfDoc) {
      pdfDoc = _pdfDoc;
      renderPage(pageNum);
    });

})();
</script>


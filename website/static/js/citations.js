/////////////////////
// Project JS      //
/////////////////////

  $(document).ready(function() {

        var $citationFormHuman = $("#citationFormHuman")
        var $citationFormHumanSelect = $citationFormHuman.find('select');

//      $(".rendered-citation").text(nodeApiUrl + 'citation/human/apa.csl');

      $.ajax({
                type: "GET",
                url: nodeApiUrl + 'citation/human/apa.csl',
            success: function(response){
                    $(".rendered-citation").text(response.output);
                    return false;
                }
            })

    $citationFormHuman.change(function(){
        $.ajax({
                type: "GET",
                url: nodeApiUrl + 'citation/human/' +$citationFormHumanSelect.val(),
            success: function(response){
                    $(".rendered-citation").text(response.output);
                    return false;
                }
            })
            return false;
        })

        var $citationFormMachine = $('#citationFormMachine');
        var $citationFormMachineSelect = $citationFormMachine.find('select');

      $citationFormMachine.on('submit', function(){
              window.location.href =nodeApiUrl + 'citation/machine/' + $citationFormMachineSelect.val() ;
               return false;
        })
  })


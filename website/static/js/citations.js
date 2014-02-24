/////////////////////
// Project JS      //
/////////////////////

  $(document).ready(function() {

        var $citationFormHuman = $("#citationFormHuman")
        var $citationFormHumanSelect = $citationFormHuman.find('select');
    $citationFormHuman.on('submit', function(){
        $.ajax({
                type: "GET",
                url: nodeApiUrl + 'citation/human/' +$citationFormHumanSelect.val() ,
//               url: nodeApiUrl + 'citation/human/' + $citationFormHuman.select().val() ,

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


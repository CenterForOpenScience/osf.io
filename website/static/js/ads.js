/* http://stackoverflow.com/questions/4869154/how-to-detect-adblock-on-my-website
 * Most adblocks will see that a file with ads in the title is attempting to be
 * imported and block it. In this case the variable won't exist, which means we will
 * enter the if.
*/
$('.ad_block_display').css({'display':'none'});

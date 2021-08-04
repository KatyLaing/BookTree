// add increment functionality to the plus/minus icons
document.addEventListener('DOMContentLoaded', function() {
  minus = document.getElementById("minus-counter");
  plus = document.getElementById("plus-counter");
  
  // minus should decrease the recorded number of reads by 1
  minus.addEventListener("click", function(){
    if(nReads > 0){
      nReads -= 1;
      document.getElementById("read-counter").innerHTML = nReads;
      $.post('/updateReads', { id: book_id, reads : nReads});
    }
    // if the book is not in progress and we now have 0 reads, change to in progress and set progress to 0%
    if(nReads == 0 && in_progress == 1){
      // set progress bar and inner text to 0%
      pagesRead = 0;
      $('#left-bar').css('transform', 'rotate(0deg)');
      $('#right-bar').css('transform', 'rotate(0deg)');
      document.getElementById('percent-read').innerHTML = "0<sup class=\"small\">%</sup>";
      // replace the read again button with the page counter and add the progress update even listener to it
      document.getElementById('progress-content').innerHTML = "<div class='h4 font-weight-bold mb-1'><input class='font-weight-bold text-center' type='number' min='0' max='" + totalPages + "' step='1' style='border: none;width: 100px' value='0'/></div><span class='small text-gray'>Pages Read</span>";
      document.querySelectorAll('input[type=number]')[0].addEventListener('change', updateProgressNoParam);
      // update in_progress to true
      in_progress = 0;
      $.post('/updateProgressStatus', { id: book_id, in_progress : 0});
    }
  });

  plus.addEventListener("click", function(){
    // plus increments the recorded number of reads by 1
    nReads += 1;
    document.getElementById("read-counter").innerHTML = nReads;
    $.post('/updateReads', { id: book_id, reads : nReads}, function(){
      // print a success message
      swal({
          title: "Well Done!",
          text: "Another book completed",
          icon: "success",
      });
      // if the book was in progress, remove any "reading progress" and set progress bar to full
      if( in_progress == 0){
        $.post('/updateProgress', { id: book_id, pages : 0});
        pagesRead = 0;
        $('#left-bar').css('transform', 'rotate(180deg)');
        $('#right-bar').css('transform', 'rotate(180deg)');
        document.getElementById('percent-read').innerHTML = "100<sup class=\"small\">%</sup>";
        // remove the event listener on the number input and replace it with the "read again" button
        document.querySelectorAll('input[type=number]')[0].removeEventListener('change', updateProgressNoParam);
        document.getElementById('progress-content').innerHTML = "<button class='btn btn-primary  mb-3 mt-2' onclick='statusInProgress(); return false;' type='submit'>Read Again?</button>";
        // update in_progress to false
        in_progress = 1;
        $.post('/updateProgressStatus', { id: book_id, in_progress : 1});
      }
    });
  });
});

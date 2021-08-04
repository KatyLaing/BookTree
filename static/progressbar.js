// function to convert number of pages read into a degree from 0 to 360
function pagesToDegrees(value, total) {
    return value / total * 360;
}

// function to return an integer percent progress from #pages read
// However, 0% and 100% will only be diplayed is 0 or all pages read
function pagePercentRound(page, totalPages) {
    percent = Math.round(100 * page / parseFloat(totalPages));
    if(percent == 0 && page > 0){
    return 1;
    }
    if(percent == 100 && page < parseInt(totalPages)){
    return 99;
    }
    return percent;
}

// function to compute exact percent of pages read
function pageToPercent(page, totalPages){
    return 100  * page/parseFloat(totalPages);
}

// global variable to record current number of pages read
var pagesRead;

// do not allow scrolling on #pages input
document.addEventListener("wheel", function(event){
    if(document.activeElement.type === "number"){
        document.activeElement.blur();
    }
});

//function for initially loading the progress bar (on page load)
function LoadProgress(totalPages){
    // find initial number of pages read
    npages = parseInt(document.querySelectorAll('input[type=number]')[0].value);
    progress_percent = document.getElementById('percent-read');
    pagesRead = npages;

    // set the progress bar to current progress
    if(pageToPercent(npages, totalPages)<=50){
        deg = pagesToDegrees(npages, parseInt(totalPages)) + "deg"
        $('#left-bar').css('transform', '');
        $('#right-bar').css('transform', 'rotate(' + deg + ')');
    }
    else{
        deg = (pagesToDegrees(npages, parseInt(totalPages)) - 180) + "deg"
        $('#right-bar').css('transform', 'rotate(180deg)');
        $('#left-bar').css('transform', 'rotate(' + deg + ')');
    }
    // update text percentage
    progress_percent.innerHTML = pagePercentRound(npages, totalPages) + '<sup class="small">%</sup>';
}

// function for updating the progress bar
function updateProgress (book_id, totalPages){
    pagesInput = document.querySelectorAll('input[type=number]')[0];
    // disable pages-read input for duration of update
    pagesInput.disabled = true;
    // find the new number of pages read
    progress_percent = document.getElementById('percent-read');
    number = pagesInput.value;
    // only update the progress bar if the input number is an integer and in the range of possible pages and has changed from previous progress
    if(number && Number.isInteger(parseFloat(number))){
        number = parseInt(number);
        if(number >= 0 && number <= parseInt(totalPages)){
            if(number != pagesRead){
                // if the update is a single page increment, update rotation of progress bar (and the percentage text) without animation
                // This allows for instantanious update of progress bar onf click of up/down arrow
                if (number == (pagesRead + 1)){
                    if(pageToPercent(pagesRead, totalPages) < 50){
                        deg = pagesToDegrees(number, parseInt(totalPages)) + "deg";
                        $('#right-bar').css('transform', 'rotate(' + deg + ')');
                    }
                    else{
                        deg = (pagesToDegrees(number, parseInt(totalPages)) - 180) + "deg";
                        $('#left-bar').css('transform', 'rotate(' + deg + ')');
                    }
                    progress_percent.innerHTML = pagePercentRound(number, totalPages) + '<sup class="small">%</sup>';
                }
                else if (number == (pagesRead - 1)){
                    if(pageToPercent(pagesRead, totalPages) <= 50){
                        deg = pagesToDegrees(number, parseInt(totalPages)) + "deg";
                        $('#right-bar').css('transform', 'rotate(' + deg + ')');
                    }
                    else{
                        deg = (pagesToDegrees(number, parseInt(totalPages)) - 180) + "deg";
                        $('#left-bar').css('transform', 'rotate(' + deg + ')');
                    }
                    progress_percent.innerHTML = pagePercentRound(number, totalPages) + '<sup class="small">%</sup>';
                }
                // if it is a non-incrememntal change, animate the movement of progress bar
                else{
                    // if current position is on left of the progress bar
                    if(pageToPercent(pagesRead, totalPages) > 50){
                        // if the new position is also on the left, then only the left hand side of progresss bar (and text) needs updating
                        if(pageToPercent(number, totalPages) >= 50){
                            deg = (pagesToDegrees(number, parseInt(totalPages)) - 180) + "deg";
                            $('#left-bar').off();
                            $('#right-bar').off();
                            $('#left-bar').transition({ rotate: deg , easing: 'easeInOutQuad'});
                            progress_percent.innerHTML = pagePercentRound(number, totalPages) + '<sup class="small">%</sup>';
                        }
                        // if the new position is on the right, change the LHS to 0 degrees and update the right hand side
                        else{
                            deg = pagesToDegrees(number, parseInt(totalPages)) + "deg";
                            $('#left-bar').off();
                            $('#right-bar').off();
                            // if we are not moving far into the RHS, the RHS animation needs to be faster
                            if(pageToPercent(number, totalPages) > 40){
                            $('#left-bar').on("transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd", function(e){$('#right-bar').transition({ rotate: deg , easing: 'easeOutQuart'});  $(this).off(e);});
                            }
                            else{
                            $('#left-bar').on("transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd", function(e){$('#right-bar').transition({ rotate: deg , easing: 'easeOutCubic'});  $(this).off(e);});
                            }
                            // if we are not currently far into the LHS, the LHS animation needs to be faster
                            if(pageToPercent(pagesRead, totalPages) < 60){
                            $('#left-bar').transition({ rotate: '0deg' , easing: 'easeInQuart'});
                            }
                            else{
                            $('#left-bar').transition({ rotate: '0deg' , easing: 'easeInCubic'});
                            }
                            progress_percent.innerHTML = pagePercentRound(number, totalPages) + '<sup class="small">%</sup>';
                        }
                    }
                    // if current position is on right of the progress bar
                    else{
                        // if the new position is also on the right, then only the right hand side of progresss bar (and text) needs updating
                        if(pageToPercent(number, totalPages) <= 50){
                            deg = pagesToDegrees(number, parseInt(totalPages)) + "deg";
                            $('#left-bar').off();
                            $('#right-bar').off();
                            $('#right-bar').transition({ rotate: deg , easing: 'easeInOutQuad'});
                            progress_percent.innerHTML = pagePercentRound(number, totalPages) + '<sup class="small">%</sup>';
                        }
                        // if the new position is on the left, change the RHS to 180 degrees and update the left hand side
                        else{
                            deg = (pagesToDegrees(number, parseInt(totalPages)) - 180) + "deg";
                            $('#left-bar').off();
                            $('#right-bar').off();
                            // if we are not moving far into the LHS, the LHS animation needs to be faster
                            if(pageToPercent(number, totalPages) < 60){
                                $('#right-bar').on("transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd", function(e){$('#left-bar').transition({ rotate: deg , easing: 'easeOutQuart'});  $(this).off(e);});
                            }
                            else{
                                $('#right-bar').on("transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd", function(e){$('#left-bar').transition({ rotate: deg , easing: 'easeOutCubic'});  $(this).off(e);});
                            }
                            // if we are not currently far into the RHS, the RHS animation needs to be faster
                            if(pageToPercent(pagesRead, totalPages) > 40){
                                $('#right-bar').transition({ rotate: '180deg' , easing: 'easeInQuart'});
                            }
                            else{
                                $('#right-bar').transition({ rotate: '180deg' , easing: 'easeInCubic'});
                            }
                            progress_percent.innerHTML = pagePercentRound(number, totalPages) + '<sup class="small">%</sup>';
                        }
                    }
                }
                // update global pages read
                pagesRead = number;
                // if the user has now read all pages, increase the number of total reads and re set the pages read to 0
                if(pagesRead == totalPages){
                    nReads += 1;
                    document.getElementById("read-counter").innerHTML = nReads;
                    $.post('/updateReads', { id: book_id, reads : nReads}, function() {
                        swal({
                            title: "Well Done!",
                            text: "Another book completed",
                            icon: "success",
                        });
                    });
                    pagesRead = 0;
                    $.post('/updateProgress', { id: book_id, pages : 0}, function(outcome){
                        if (outcome == 'Failed'){
                            swal({
                                title: "Could not update your reading progress",
                                icon: "warning",
                            })
                        }
                        pagesInput.disabled = false;
                    });
                    // change "in progress" to 1
                    in_progress = 1;
                    $.post('/updateProgressStatus', { id: book_id, in_progress : 1});
                    // remove the update event listener from the page number input and replace with "read again" button
                    document.querySelectorAll('input[type=number]')[0].removeEventListener('change', updateProgressNoParam);
                    document.getElementById('progress-content').innerHTML = "<button class='btn btn-primary  mb-3 mt-2' onclick='statusInProgress(); return false;'' type='submit'>Read Again?</button>";

                }
                // itherwise, simply update the page value in user data base
                else{
                    $.post('/updateProgress', { id: book_id, pages : pagesRead}, function(outcome){
                        if (outcome == 'Failed'){
                            swal({
                                title: "Could not update your reading progress",
                                icon: "warning",
                            })
                        }
                        pagesInput.disabled = false;
                    });
                }
            }
            else{
                pagesInput.disabled = false;
            } 
        }
        else{
            pagesInput.disabled = false;
        }
    }
    else{
        pagesInput.disabled = false;
    }
    
}
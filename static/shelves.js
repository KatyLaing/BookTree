
document.addEventListener('DOMContentLoaded', function() {
    add_shelf_btn = document.getElementById("add-shelf");
    // when add shelf button clicked, pop up form, submit to DB and display the result
    // if success ful, reload the page to shelf list updates
    add_shelf_btn.addEventListener('click', function(){
        swal("Add a New Shelf:", {
            content: "input",
        })
        .then((value) => {
            value = value.trim();
            if(!value){
                swal({
                    title: "Shelves must have a non-empty name",
                    icon: "warning",
                    dangerMode: true,
                });
            }
            else{
                $.post('/addShelf', { name: value }, function(outcome){
                    if(outcome == 'empty'){
                        swal({
                            title: "Shelves must have a non-empty name",
                            icon: "warning",
                            dangerMode: true,
                        });
                    }
                    if(outcome == 'repeat'){
                        swal({
                            title: "Cannot have two shelves with the same name",
                            icon: "warning",
                            dangerMode: true,
                        });
                    }
                    if(outcome == 'error'){
                        swal({
                            title: "Shelf could not be added",
                            icon: "warning",
                            dangerMode: true,
                        });
                    }
                    if(outcome == 'success'){
                        swal({
                        title: "Shelf added to your library!",
                        icon: "success",
                        }).then((value) => {
                            // if we are in a book summary page, we need to re-submit the post request to reload the page
                            if(window.location.href == "http://" + window.location.host + "/book-summary#"){
                                book_id = document.getElementsByClassName('BookId')[0].value;
                                // funciton defined in add_remove_books.js
                                PostBookSummary(book_id);
                            }
                            else{
                                window.location.reload();
                            }
                        });
                    }
                    
                });
            }
        });
    });
});
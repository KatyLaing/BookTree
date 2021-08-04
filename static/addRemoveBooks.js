// a function for submitting post requests for book summaries
function PostBookSummary(booktag){
    method = 'post';
    let form = document.createElement('form');
    form.setAttribute('method', method);
    form.setAttribute('action', '/book-summary');
    let hiddenField = document.createElement('input');
    hiddenField.setAttribute('type', 'hidden');
    hiddenField.setAttribute('name', 'booktag');
    hiddenField.setAttribute('value', booktag);
    form.appendChild(hiddenField);

    document.body.appendChild(form);
    form.submit();
}

//a function to add the books to lib
function addlib(e, reload=false){
    //identify the button clicked
    let book_id = document.getElementsByClassName('BookId')[e.id].value;
    let wish_id = (parseInt(e.id) + 1)
    let wish_button = document.getElementById(wish_id)
    //disable all buttons, re-enable when SQL alterations complete
    $(':button').prop('disabled', true);
    //add the book to library and remove from wishlist
    $.post('/addtolib', {id: book_id}, function(){
        $.post('/removeFromWish', {id: book_id}, function(){
            $(':button').prop('disabled', false);
            if(reload){
                PostBookSummary(book_id);
            }
        });
    });
    // change button to be a remove from library button:
    e.classList.remove("add-lib");
    e.classList.add("remove-book");
    e.onclick = function() {removelib(this, reload); return false;};
    icon = e.getElementsByClassName('fa-plus-square')[0]
    icon.classList.remove("fa-plus-square");
    icon.classList.add("fa-minus-square");
    text = e.getElementsByClassName('button_content')[1]
    text.innerHTML = "Remove From Library";
    // change wishlist button to and "add to WL" button
    wish_button.classList.remove("remove-book");
    wish_button.classList.add("add-wishl");
    wish_button.onclick = function() {addwish(this); return false;};
    icon = wish_button.getElementsByClassName('fa-star')[0]
    icon.classList.remove("fas");
    icon.classList.add("far");
    text = wish_button.getElementsByClassName('button_content')[1]
    text.innerHTML = "Add To Wishlist";
    return false;
}

//a function to add the books to WL
function addwish(e){
    let book_id = document.getElementsByClassName('BookId')[e.id].value;
    $(':button').prop('disabled', true);
    $.post('/addtowishl', {id: book_id}, function(outcome){
        if(outcome == 'success'){
            e.classList.remove("add-wishl");
            e.classList.add("remove-book");
            e.onclick = function() {removewish(this); return false;};
            icon = e.getElementsByClassName('fa-star')[0]
            icon.classList.remove("far");
            icon.classList.add("fas");
            text = e.getElementsByClassName('button_content')[1]
            text.innerHTML = "Remove From Wishlist";
        }
        else if (outcome == 'inLib'){
            swal({
                title: "Title not added to wishlist",
                text: "This book is already in your library",
                icon: "warning",
            })
        }
        else if (outcome == 'error'){
            swal({
                title: "Title not added to wishlist",
                text: "An unexpected error occurred",
                icon: "warning",
            });
        }
        else {
            swal({
                title: "Error",
                icon: "warning",
            });
        }
        $(':button').prop('disabled', false);
    });
    return false;
}

// function for removing books from lib
function removelib(e, reload=false){
    //get the id of the book
    let book_id = document.getElementsByClassName('BookId')[e.id].value;
    //disable all buttons until SQL transaction complete
    $(':button').prop('disabled', true);
    //remove this books from the user's library:
    $.post('/removeFromLib', {id: book_id}, function(){
        if(reload){
            PostBookSummary(book_id);
        }
        $(':button').prop('disabled', false);
    });
    e.classList.remove("remove-book");
    e.classList.add("add-lib");
    e.onclick = function() {addlib(this, reload); return false;};
    icon = e.getElementsByClassName('fa-minus-square')[0]
    icon.classList.remove("fa-minus-square");
    icon.classList.add("fa-plus-square");
    text = e.getElementsByClassName('button_content')[1]
    text.innerHTML = "Add To Library";
    return false;
}

// function for removing books from WL
function removewish(e){
    //get the id of the book
    let book_id = document.getElementsByClassName('BookId')[e.id].value;
    //disable all buttons until SQL transaction complete
    $(':button').prop('disabled', true);
    //remove this books from the user's library:
    $.post('/removeFromWish', {id: book_id}, function(){
        $(':button').prop('disabled', false);
    });
    e.classList.remove("remove-book");
    e.classList.add("add-wishl");
    e.onclick = function() {addwish(this); return false;};
    icon = e.getElementsByClassName('fa-star')[0]
    icon.classList.remove("fas");
    icon.classList.add("far");
    text = e.getElementsByClassName('button_content')[1]
    text.innerHTML = "Add To Wishlist";
    return false;
}

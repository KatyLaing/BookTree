// Display the results  of a search or sort in the Library or default shelves
function LibSortSearchDisplay (books){
    let table_contents = '<tr>';

    for (let id in books){
        let title = books[id].title;
        let subtitle = books[id].subtitle;
        let yr = books[id].year;
        let authors = books[id].authors;
        let format = books[id].format;
        let cover = books[id].thumbnail;
        let google_id = books[id].google_id;
        let rating = books[id].rating;

        table_row = '<td><div class="form-check form-check-inline ml-3"><input type="checkbox" class="form-check-input filled-in" form="AddToShelf" name="Book" value="'  + google_id + '" style="width: 20px; height: 20px;"></div></td>';

        if(cover){
            table_row+= '<td><img src="' + cover + '"></td>';
        }
        else{
            table_row+= '<td><img src="static/bookcase.jpg"></td>'
        }
        table_row+= '<td><form  action="/book-summary" method="post"><input name="booktag" type="hidden" value="' + google_id + '"><button class="book-link" type=submit>' + title;
        if(subtitle){
            table_row+= ' - ' + subtitle;
        }
        table_row+= '</button></form></td>';
        table_row+= '<td>' + authors + '</td>';
        table_row+= '<td>' + yr + '</td>';
        if(format === 'Book'){
            table_row+= '<td><img src="/static/bookfavicon.ico" alt="Book logo"></td>';
        }
        if(format === 'Ebook'){
            table_row+= '<td><img src="/static/phonefavicon.ico" alt="Phone logo"></td>';
        }
        if(format === 'Unknown'){
            table_row+= '<td><img src="/static/questionfavicon.ico" alt="Question Mark"></td>';
        }
        table_row+= '<td><span class="fa-stack fa-2x"><i class="fas fa-star fa-stack-2x" style="color:#FD4"></i><span class="fa fa-stack-1x" style="display:block;margin-left:4px;"><span style="font-size:25px;font-family: sans-serif;">' + rating + '</span></span></span></td>';
        table_row+= '<td><form><input type="hidden" class="BookId" name="BookId" value="' + google_id + '"><button class="remove-book ml-3" id="' + id + '" onclick="removelib(this); return false;" type="submit" style="width: 180px"><span class="button_content button_icon"><i class="far fa-minus-square fa-2x"></i></span><span class="button_content">Remove From Library</span></button></form></td>'
        table_contents += '<tr>' + table_row + '</tr>';
    }
    
    document.getElementsByTagName("tbody")[0].innerHTML = table_contents;

    //add the event listeners to the check boxes
    $('.form-check-input').change(function(){
        if(this.checked == false){
            $('#SelectAll')[0].checked = false;
        }
    });
}

//Function for searching the user's books in Library or Default shelves
function LibSearchBooks(){
    //disable all buttons/ sort selections for function duration
    document.getElementById("sort").disabled = true;
    $(':button').prop('disabled', true);
    // get the shelf name
    let shelf_name = document.getElementById("shelf-name").value;
    let shelf_input_dict = {"My Library" : "all", "In Progress" : "in-progress", "Unread" : "unread", "Read" : "read"};
    let shelf_input = shelf_input_dict[shelf_name];
    // get the search term
    let book_search = document.getElementById("book-search").value;
    // get the search method
    let search_method = document.getElementById("search-method").value;
    // only proceed if a search method and term is specified
    if(book_search && search_method){
        $.post('/sortAndSearchBooks', { sort: "az-title", shelf : shelf_input, search_term :  book_search, search_method : search_method}, function(books){
            // display the search results
            LibSortSearchDisplay(books)
            // record the current search & method 
            document.getElementById("current-search").value = book_search;
            document.getElementById("current-search-method").value = search_method;
            // reset the sort selection
            document.getElementById("sort").selectedIndex = 0
            document.getElementById("sort").disabled = false;
            $(':button').prop('disabled', false);
        });
    }
    else{
        // if form incorrectly filled out display a warning
        swal({
            title: "Please Specify Both a Search Term and Method",
            icon: "warning",
            dangerMode: true,
        });
        sort_select.disabled = false;
        $(':button').prop('disabled', false);
    }
}

// Display the results  of a search or sort in the custom shelves
function BookshelfSortSearchDisplay (books){
    let table_contents = '<tr>';

    for (let id in books){
        let title = books[id].title;
        let subtitle = books[id].subtitle;
        let yr = books[id].year;
        let authors = books[id].authors;
        let format = books[id].format;
        let cover = books[id].thumbnail;
        let google_id = books[id].google_id;
        let rating = books[id].rating;
        
        if(cover){
            table_row= '<td><img src="' + cover + '"></td>';
        }
        else{
            table_row= '<td><img src="static/bookcase.jpg"></td>'
        }
        table_row+= '<td><form  action="/book-summary" method="post"><input name="booktag" type="hidden" value="' + google_id + '"><button class="book-link" type=submit>' + title;
        if(subtitle){
            table_row+= ' - ' + subtitle;
        }
        table_row+= '</button></form></td>';
        table_row+= '<td>' + authors + '</td>';
        table_row+= '<td>' + yr + '</td>';
        if(format === 'Book'){
            table_row+= '<td><img src="/static/bookfavicon.ico" alt="Book logo"></td>';
        }
        if(format === 'Ebook'){
            table_row+= '<td><img src="/static/phonefavicon.ico" alt="Phone logo"></td>';
        }
        if(format === 'Unknown'){
            table_row+= '<td><img src="/static/questionfavicon.ico" alt="Question Mark"></td>';
        }
        table_row+= '<td><span class="fa-stack fa-2x"><i class="fas fa-star fa-stack-2x" style="color:#FD4"></i><span class="fa fa-stack-1x" style="display:block;margin-left:4px;"><span style="font-size:25px;font-family: sans-serif;">' + rating + '</span></span></span></td>';
        table_row+= '<td><form><input type="hidden" class="BookId" name="BookId" value="' + google_id + '"><button class="remove-book" id="' + id + '" onclick="removebookfromshelf(this); return false;" type="submit" style="width: 200px; height:55px"><span class="button_content button_icon"><i class="far fa-minus-square fa-2x"></i></span><span class="button_content">Remove From Shelf</span></button></form></td>';
        table_contents += '<tr>' + table_row + '</tr>';
    }
    
    document.getElementsByTagName("tbody")[0].innerHTML = table_contents;
}

//Function for searching the user's books in custom shelves
function BookhelfSearchBooks(){
    //disable all buttons/ sort selections for function duration
    document.getElementById("sort").disabled = true;
    $(':button').prop('disabled', true);
    // get the shelf id
    let shelf_id = document.getElementsByClassName('ShelfId')[0].value;
    // get the search term
    let book_search = document.getElementById("book-search").value;
    // get the search method
    let search_method = document.getElementById("search-method").value;
    // only proceed if a search method and term is specified
    if(book_search && search_method){
        $.post('/sortAndSearchBooks', { sort: "az-title", shelf : shelf_id, search_term :  book_search, search_method : search_method}, function(books){
            // display the search results
            BookshelfSortSearchDisplay(books)
            // record the current search & method 
            document.getElementById("current-search").value = book_search;
            document.getElementById("current-search-method").value = search_method;
            // reset the sort selection
            document.getElementById("sort").selectedIndex = 0
            document.getElementById("sort").disabled = false;
            $(':button').prop('disabled', false);
        });
    }
    else{
        // if form incorrectly filled out display a warning
        swal({
            title: "Please Specify Both a Search Term and Method",
            icon: "warning",
            dangerMode: true,
        });
        sort_select.disabled = false;
        $(':button').prop('disabled', false);
    }
}

// Display the results  of a search or sort in the Wishlist
function WishlSortSearchDisplay (books){
    let table_contents = '<tr>';

    for (let id in books){
        let title = books[id].title;
        let subtitle = books[id].subtitle;
        let yr = books[id].year;
        let authors = books[id].authors;
        let format = books[id].format;
        let cover = books[id].thumbnail;
        let google_id = books[id].google_id;

        if(cover){
            table_row= '<td><img src="' + cover + '"></td>';
        }
        else{
            table_row= '<td><img src="static/bookcase.jpg"></td>'
        }
        table_row+= '<td><form  action="/book-summary" method="post"><input name="booktag" type="hidden" value="' + google_id + '"><button class="book-link" type=submit>' + title;
        if(subtitle){
            table_row+= ' - ' + subtitle;
        }
        table_row+= '</button></form></td>';
        table_row+= '<td>' + authors + '</td>';
        table_row+= '<td>' + yr + '</td>';
        if(format === 'Book'){
            table_row+= '<td><img src="/static/bookfavicon.ico" alt="Book logo"></td>';
        }
        if(format === 'Ebook'){
            table_row+= '<td><img src="/static/phonefavicon.ico" alt="Phone logo"></td>';
        }
        if(format === 'Unknown'){
            table_row+= '<td><img src="/static/questionfavicon.ico" alt="Question Mark"></td>';
        }
        table_row+= '<td><form><input type="hidden" class="BookId" name="BookId" value="' + google_id + '"><button class="add-lib" id="' + 2*id + '" onclick="addlib(this); return false;" type="submit"><span class="button_content button_icon"><i class="far fa-plus-square fa-2x"></i></span><span class="button_content">Add To Library</span></button></form></td>';
        table_row+= '<td><form><input type="hidden" class="BookId" name="BookId" value="' + google_id + '"><button class="remove-book" id="' + (2*id + 1) + '" onclick="removewish(this); return false;" type="submit"><span class="button_content button_icon"><i class="fas fa-star fa-2x"></i></span><span class="button_content">Remove From Wishlist</span></button></form></td>';
        table_contents += '<tr>' + table_row + '</tr>';
    }
    
    document.getElementsByTagName("tbody")[0].innerHTML = table_contents;
}

//Function for searching the user's wishlist
function WishlSearchBooks(){
    //disable all buttons/ sort selections for function duration
    document.getElementById("sort").disabled = true;
    $(':button').prop('disabled', true);
    // get the search term
    let book_search = document.getElementById("book-search").value;
    // get the search method
    let search_method = document.getElementById("search-method").value;
    // only proceed if a search method and term is specified
    if(book_search && search_method){
        $.post('/sortAndSearchBooks', { sort: "az-title", shelf : "wishl", search_term :  book_search, search_method : search_method}, function(books){
            // display the search results
            WishlSortSearchDisplay(books)
            // record the current search & method 
            document.getElementById("current-search").value = book_search;
            document.getElementById("current-search-method").value = search_method;
            // reset the sort selection
            document.getElementById("sort").selectedIndex = 0
            document.getElementById("sort").disabled = false;
            $(':button').prop('disabled', false);
        });
    }
    else{
        // if form incorrectly filled out display a warning
        swal({
            title: "Please Specify Both a Search Term and Method",
            icon: "warning",
            dangerMode: true,
        });
        sort_select.disabled = false;
        $(':button').prop('disabled', false);
    }
}
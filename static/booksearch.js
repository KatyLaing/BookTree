// A function that submits the book search tot he server and displays the results
function booksearch(){
    let descrip = document.querySelector("#bookSearch").value;
    let isbn = document.querySelector("#isbn").value;
    document.querySelector("#bookSearch").value="";
    document.querySelector("#isbn").value = "";
    let results=document.querySelector('#results');
    spinnerhtml = '<div class="loadingio-spinner-spinner-tri4oabkm2j"><div class="ldio-ys4dw0ydn3"><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div></div></div>';
    results.innerHTML = spinnerhtml;
    $.post('/query', {isbn: isbn, desc: descrip}, function(books){
        let list='<table class="styled-table"><thead><tr><th>Cover</th><th>Title</th><th>Author(s)</th><th>Year</th><th>Book/Ebook</th><th></th><th></th></tr></thead><tbody>';
        for (let id in books){
            let title = books[id].title;
            let subtitle = books[id].subtitle;
            let yr = books[id].year;
            let authors = books[id].authors;
            let ebook = books[id].ebook;
            let cover = books[id].cover;
            let book_id = books[id].id;
            let suffix = books[id].suffix;
            let inlib = books[id].inlib;
            let inwish = books[id].inwish;
            
            if(cover){
                list += '<tr><td><img src="' + cover + '"></td>';
            }
            else {
                list += '<tr><td><img src="static/bookcase.jpg"></td>';
            }

            list += '<td><form  action="/book-summary" method="post"><input name="booktag" type="hidden" value="' + book_id + '">';
            list += '<button class="book-link" type=submit>' + title;

            if(subtitle){
                list+= ' - ' + subtitle;
            }
            
            list += '</button></form></td><td>' + authors + '</td><td>' + yr + '</td>';
            if(ebook === 'Unknown'){
                list+= '<td><img src="/static/questionfavicon.ico" alt="Question Mark"></td>';
            } else if(ebook){
                list += '<td><img src="/static/phonefavicon.ico" alt="Phone logo"></td>';
            } else{
                list+= '<td><img src="/static/bookfavicon.ico" alt="Phone logo"></td>';
            }
            if(inlib){
                list += '<td><form><input type="hidden" class="BookId" name="BookId" value=' + book_id + suffix + '><button class="remove-book" id="' + (2*id) + '" onclick="removelib(this); return false;" type="submit"><span class="button_content button_icon"><i class="far fa-minus-square fa-2x"></i></span><span class="button_content">Remove From Library</span></button></form></td>'
            }
            else{
                list += '<td><form><input type="hidden" class="BookId" name="BookId" value=' + book_id + suffix + '><button class="add-lib" id="' + (2*id) + '" onclick="addlib(this); return false;" type="submit"><span class="button_content button_icon"><i class="far fa-plus-square fa-2x"></i></span><span class="button_content">Add To Library</span></button></form></td>'
            }
            if(inwish){
                list += '<td><form><input type="hidden" class="BookId" name="BookId" value=' + book_id + suffix + '><button class="remove-book" id="' + (2*id + 1) + '" onclick="removewish(this); return false;" type="submit"><span class="button_content button_icon"><i class="fas fa-star fa-2x"></i></span><span class="button_content">Remove From Wishlist</span></button></form></td>'
            }
            else{
                list += '<td><form><input type="hidden" class="BookId" name="BookId" value=' + book_id + suffix + '><button class="add-wishl" id="' + (2*id + 1) + '" onclick="addwish(this); return false;" type="submit"><span class="button_content button_icon"><i class="far fa-star fa-2x"></i></span><span class="button_content">Add To Wishlist</span></button></form></td>'
            }
            list +='</tr>'
        }
        list += '</tbody></table>';
        if(books.length == 0){
            list += '<p><h2 class="h6 font-weight-bold text-center mb-4">No results found <i class="far fa-frown"></i></h2></p>';
        }
        results.innerHTML = list;
    });
}
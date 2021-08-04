import http
import json
import os
import re
import sqlite3

from datetime import datetime
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from isbnlib import is_isbn10, is_isbn13, cover, meta
from markupsafe import Markup
from passlib.hash import sha256_crypt
from tempfile import mkdtemp
from urllib.request import urlopen

from additionalFunctions import add_book_to_db, add_isbn_to_db, dict_factory, google_results_to_list, isbn_results_to_list, login_required, stock_check

#example of getting variables from the environment
GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API")

app = Flask(__name__)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#load homepage
@app.route("/")
def index():
    return render_template("index.html")

# add the new shelf
@app.route("/addShelf", methods=["POST"])
@login_required
def addShelf():
    shelf = request.form['name']
    user_id = session["user_id"]

    #ensure that the name is non-empty
    try:
        shelf = shelf.strip().title()
        if not shelf:
            return 'empty'
    except:
        return 'error'
    
    #ensure that the user doesn't already have a shelf with this name
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    shelf_id = cur.execute("SELECT id FROM shelves WHERE shelf=? AND id IN (SELECT shelf_id FROM user_shelves WHERE user_id=?)", (shelf, user_id,)).fetchall()
    if len(shelf_id) > 0:
        cur.execute("COMMIT")
        con.close()
        return 'repeat'
    
    # otherwise add the shelf and return the ID
    shelf_id = cur.execute("INSERT INTO shelves (shelf) VALUES (?)", (shelf,)).lastrowid
    # link the user with the shelf
    cur.execute("INSERT INTO user_shelves (user_id, shelf_id) VALUES (?, ?)", (user_id, shelf_id,))
    cur.execute("COMMIT")
    con.close()
    
    #add the shelf to the user's session
    session["shelves"][str(shelf_id)] = shelf
    return 'success'

# add specified book to user's library
@app.route("/addtolib", methods=["POST"])
@login_required
def addlib():
    # get id from button clicked
    button_id = request.form.get("id")
    # if this is an ISBN we must separate the id into ISBN and suffix (if present)
    if button_id[0:4] == 'ISBN':
        method = 'isbn'
        if button_id[-5:] == 'openl':
            id = button_id[:-5]
            suffix = 'openl'
        elif button_id[-4:] == 'wiki':
            id = button_id[:-4]
            suffix = 'wiki'
        else:
            id = button_id
            suffix = 'unknown'
    #otherwise the button id gives us the google id
    else:
        method = 'gbooks'
        id = button_id
    # get the user's id:
    user_id = session["user_id"]
    # determine whether this book is already in the global library
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    row=cur.execute("SELECT (id) FROM books WHERE google_id=?", (id,))
    row = row.fetchall()
    # if the book data is already present then add it to user's library (if not already present)
    if len(row) == 1:
        book_id = row[0]['id']
        lib_row = cur.execute("SELECT * FROM library WHERE user_id=? AND book_id=?", (user_id, book_id)).fetchall()
        if len(lib_row) == 0:
            cur.execute("INSERT INTO library (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
        cur.execute("COMMIT")
        con.close()
        return 'success'
    else:
        cur.execute("COMMIT")
        #if book has not been recorded previously, add it to the DB
        if method == 'gbooks':
            book_id = add_book_to_db(id)
        if method == 'isbn':
            book_id = add_isbn_to_db(id, suffix)
        # if it could not be added to DB due to invalid google id or isbn, exit the function
        if book_id == 0:
            con.close()
            return 'Failure'
        #add the book to the user's library
        while True:
            try:
                cur.execute("BEGIN IMMEDIATE")
                break
            except:
                pass
        try:
            cur.execute("INSERT INTO library (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
        except:
            pass
        #comit and close DB
        cur.execute("COMMIT")
        con.close()
        return 'success'

# add the specified book to the given shelf
@app.route("/addtoshelf", methods=["POST"])
@login_required
def addtoshelf():
    #get the shelf id, book IDs, and user ID
    try:
        shelf_id = request.form['shelves']
    except:
        return ('', http.HTTPStatus.BAD_REQUEST)
    book_ids = request.form.getlist('Book')
    user_id = session["user_id"]

    #check that the shelf ID is a positive integer:
    try:
        shelf_id = int(shelf_id)
        if shelf_id < 1:
            return ('', http.HTTPStatus.BAD_REQUEST)
    except:
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    #check that at least one book has been selected
    if len(book_ids) == 0:
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    #check that the specified shelf belongs to this user
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    shelf_row = cur.execute("SELECT * FROM user_shelves WHERE shelf_id=? AND user_id=?", (shelf_id, user_id,)).fetchall()
    if len(shelf_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    #for each specified book, check that it belongs to the user's library and if so add to shelf
    #if any book does not belowng in library, terminate function
    for book_tag in book_ids:
        book_row = cur.execute("SELECT id FROM books WHERE google_id=?", (book_tag,)).fetchall()
        if len(book_row) == 0:
            cur.execute("COMMIT")
            con.close()
            return ('', http.HTTPStatus.BAD_REQUEST)
        book_id = book_row[0]['id']
        book_row = cur.execute("SELECT book_id FROM library WHERE book_id=? AND user_id=?", (book_id, user_id,)).fetchall()
        if len(book_row) == 0:
            cur.execute("COMMIT")
            con.close()
            return ('', http.HTTPStatus.BAD_REQUEST)
        try:
            cur.execute("INSERT INTO book_shelves (book_id, shelf_id) VALUES (?, ?)", (book_id, shelf_id,))
        except:
            pass
    
    cur.execute("COMMIT")
    con.close()
    return redirect("/bookshelf?shelf_id="+str(shelf_id))

#add specified book to the user's wishlist
@app.route("/addtowishl", methods=["POST"])
@login_required
def addwish():
    
    # get id from button clicked
    button_id = request.form.get("id")
    # if this is an ISBN we must separate the id into ISBN and suffix (if present)
    if button_id[0:4] == 'ISBN':
        method = 'isbn'
        if button_id[-5:] == 'openl':
            id = button_id[:-5]
            suffix = 'openl'
        elif button_id[-4:] == 'wiki':
            id = button_id[:-4]
            suffix = 'wiki'
        else:
            id = button_id
            suffix = 'unknown'
    #otherwise the button id gives us the google id
    else:
        method = 'gbooks'
        id = button_id
    # get the user's id:
    user_id = session["user_id"]
    # determine whether this book is already in the global library
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    row=cur.execute("SELECT (id) FROM books WHERE google_id=?", (id,))
    row = row.fetchall()
    # if the book data is already present, first check it is not in library (in which case do not add it to WL)
    # otherwise add it to user's wishlist (if not already present)
    if len(row) == 1:
        book_id = row[0]['id']
        lib_row = cur.execute("SELECT * FROM library WHERE user_id=? AND book_id=?", (user_id, book_id)).fetchall()
        if len(lib_row) > 0:
            cur.execute("COMMIT")
            con.close()
            return 'inLib'
        wish_row = cur.execute("SELECT * FROM wishlist WHERE user_id=? AND book_id=?", (user_id, book_id)).fetchall()
        if len(wish_row) == 0:
            cur.execute("INSERT INTO wishlist (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
        cur.execute("COMMIT")
        con.close()
        return 'success'
    else:
        cur.execute("COMMIT")
        #if book has not been recorded previously, addd it to the library
        if method == 'gbooks':
            book_id = add_book_to_db(id)
        if method == 'isbn':
            book_id = add_isbn_to_db(id, suffix)
        # if it could not be added to DB due to invalid google id or isbn, exit the function
        if book_id == 0:
            con.close()
            return 'error'
        #add the book to the user's wihlist
        while True:
            try:
                cur.execute("BEGIN IMMEDIATE")
                break
            except:
                pass
        try:
            cur.execute("INSERT INTO wishlist (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
        except:
            pass
        #comit and close DB
        cur.execute("COMMIT")
        con.close()
        return 'success'

# display the requested custom shelf
@app.route("/bookshelf", methods=["GET"])
@login_required
def bookshelf():
    shelf_id = request.args['shelf_id']
    user_id=session["user_id"]
    
    # if no id specified, redirect to home
    if not shelf_id:
        flash('Could not load bookshelf', 'error')
        return redirect("/")
    
    # check that the shelf belongs to this user
    con = sqlite3.connect('booktree.db')
    con.row_factory = dict_factory
    cur=con.cursor()

    row = cur.execute("SELECT * FROM user_shelves WHERE user_id=? AND shelf_id=?", (user_id, shelf_id,)).fetchall()
    if len(row) == 0:
        con.close()
        flash('Could not load bookshelf', 'error')
        return redirect("/")
    
    #obtain the shelf name
    shelf_name = cur.execute("SELECT shelf FROM shelves WHERE id=?", (shelf_id,)).fetchall()[0]['shelf']

    # obtain the data for all of the books on this shelf
    sqlrequest = "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail, library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE library.user_id=? AND books.id IN (SELECT book_id FROM book_shelves WHERE shelf_id=?)"
    book_rows = cur.execute(sqlrequest, (user_id, shelf_id,)).fetchall()
    
    #obtain the authors for each book
    authorsqlrequest = "SELECT authors.name FROM authors JOIN book_authors ON authors.id = book_authors.author_id JOIN books ON book_authors.book_id=books.id WHERE books.id=?"
    for book in book_rows:
        author_rows = cur.execute(authorsqlrequest, (book['id'],)).fetchall()
        #assemble a list of tuples where each tuple is a lastname, firstname pair corresponding to one author
        authorTuples = []
        n = len(author_rows)
        for i in range(n):
            author = author_rows[i]['name']
            author_list = author.split()
            first_name = ' '.join(author_list[:-1])
            last_name = author_list[-1:][0]
            authorTuples.append((last_name, first_name))
        # sort the author tuples into alphabetical order and then assemble them into a string
        authorTuples.sort()
        author_str = ', '.join(' '.join([y, x]) for x, y in authorTuples)
        # add the authors to the book data
        book["authors"] = author_str

    con.close()

    #return the shelf name and contents to the shelf template
    return render_template("bookshelf.html", shelf_name=shelf_name, shelf_id=shelf_id, shelf_size=len(book_rows), books=enumerate(book_rows))

#display book summary page for requested book
@app.route("/book-summary", methods=["POST"])
@login_required
def booksummary():
    # get the book id from submission
    book_id = request.form.get("booktag")
    if not book_id:
        return render_template("nobook.html")
    #get the user's id
    user_id = session["user_id"]
    # if the book is already in the DB extract it's data:
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    row = cur.execute("SELECT * FROM books WHERE google_id=?", (book_id,)).fetchall()
    cur.execute("COMMIT")
    if(len(row) == 1):
        book_key = row[0]['id']
        #ensure the description is parsed as HTML
        row[0]['descrip'] = Markup(row[0]['descrip'])
        #add the format
        format = cur.execute("SELECT format FROM format WHERE id=?", (row[0]['format_id'],)).fetchall()[0]['format']
        row[0]['format'] = format
        #add the publisher explicitly
        if not row[0]['pub_id'] == 0:
            publisher = cur.execute("SELECT publisher FROM publisher WHERE id=?", (row[0]['pub_id'],)).fetchall()[0]['publisher']
        else:
            publisher = ""
        row[0]['publisher'] = publisher
        #add the language explicitly
        if not row[0]['lang_id'] == 0:
            language = cur.execute("SELECT language FROM languages WHERE id=?", (row[0]['lang_id'],)).fetchall()[0]['language']
        else:
            language = ""
        row[0]['language'] = language

        #add string of authors
        author_rows = cur.execute("SELECT name FROM authors JOIN book_authors ON authors.id=book_authors.author_id WHERE book_id=?", (book_key,)).fetchall()
        #assemble a list of tuples where each tuple is a lastname, firstname pair corresponding to one author
        authorTuples = []
        n = len(author_rows)
        for i in range(n):
            author = author_rows[i]['name']
            author_list = author.split()
            first_name = ' '.join(author_list[:-1])
            last_name = author_list[-1:][0]
            authorTuples.append((last_name, first_name))
        # sort the author tuples into alphabetical order and then assemble them into a string
        authorTuples.sort()
        author_str = ', '.join(' '.join([y, x]) for x, y in authorTuples)
        # add the authors to the book data
        row[0]['authors'] = author_str
        #add a list of categories:
        cats = []
        cat_rows = cur.execute("SELECT category FROM categories JOIN book_categories ON categories.id=book_categories.cat_id WHERE book_id=?", (book_key,)).fetchall()
        for item in cat_rows:
            cats.append(item['category'])
        row[0]['categories'] = cats
        #now determine whether the book is in the user's library, wishlist, or neither
        #if the book is in the users library, add the extra user data
        user_book_data = {}
        while True:
            try:
                cur.execute("BEGIN IMMEDIATE")
                break
            except:
                pass
        lib_row = cur.execute("SELECT * FROM library WHERE user_id=? AND book_id=?", (user_id,book_key,)).fetchall()
        if len(lib_row) == 1:
            user_book_data['owned'] = "inLib"
            user_book_data['rating'] = lib_row[0]['rating']
            user_book_data['notes'] = lib_row[0]['notes']
            user_book_data['pages_read'] = lib_row[0]['pages_read']
            user_book_data['number_of_reads'] = lib_row[0]['nReads']
            user_book_data['date_added'] = lib_row[0]['date_added']
            user_book_data['date_modified'] = lib_row[0]['date_modified']
            user_book_data['in_progress'] = lib_row[0]['in_progress']
        else:
            wl_row = cur.execute("SELECT * FROM wishlist WHERE user_id=? AND book_id=?", (user_id,book_key,)).fetchall()
            if len(wl_row) == 1:
                user_book_data['owned'] = "inWL"
            else:
                user_book_data['owned'] = "neither"
        cur.execute("COMMIT")
        con.close()
        #render the book sumary page with this information
        return render_template("bookinfo.html", book_data=row[0], user_data=user_book_data)
    con.close()
    # if the book is not in the DB we will need to re-extract the information from APIs
    user_book_data = {'owned' : 'neither'}
    # first we deal with the ISBN case
    if book_id[0:4] == "ISBN":
        try:
            results = meta(book_id)
            if len(results.keys()) == 0:
                try:
                    results = meta(id, 'openl')
                except:
                    return render_template("nobook.html")
        except:
            try:
                results = meta(book_id, 'openl')
            except:
                return render_template("nobook.html")
        if len(results.keys()) == 0:
            return render_template("nobook.html")
        book_data = {}
        book_data['format'] = 'Unknown'
        book_data['google_id'] = book_id
        book_data['descrip'] = ''
        book_data['pages'] = None
        book_data['url'] = ''
        book_data['categories'] = []
        try:
            book_data['language'] = results['Language']
        except:
            book_data['language'] = ""
        try:
            book_data['title'] = results['Title']
        except:
            book_data['title'] = ""
        try:
            book_data['subtitle'] = results['Subtitle']
        except:
            book_data['subtitle'] = ""
        try:
            book_data['year'] = results['Year']
        except:
            book_data['year'] = None
        try:
            book_data['isbn10'] = results['ISBN-10']
        except:
            book_data['isbn10'] = ""
        try:
            book_data['isbn13'] = results['ISBN-13']
        except:
            book_data['isbn13'] = ""
        try:
            book_data['publisher'] = results['Publisher']
        except:
            book_data['publisher'] = ""
        try:
            authors = results['Authors']
            n = len(authors)
            authorTuples = []
            for i in range(n):
                author = authors[i]
                author_list = author.split()
                first_name = ' '.join(author_list[:-1])
                last_name = author_list[-1:][0]
                authorTuples.append((last_name, first_name))
            # sort the author tuples into alphabetical order and then assemble them into a string
            authorTuples.sort()
            author_str = ', '.join(' '.join([y, x]) for x, y in authorTuples)
            # add the authors to the book data
            book_data['authors'] = author_str
        except:
            book_data['authors'] = ""
        
        try:
            image_links = cover(book_id)
            try:
                thumbnail = image_links['smallThumbnail']
            except:
                try:
                    thumbnail = image_links['thumbnail']
                except:
                    thumbnail = ""
            if "&edge=curl" in thumbnail:
                thumbnail = thumbnail.replace("&edge=curl", "")
            if "edge=curl&" in thumbnail:
                thumbnail = thumbnail.replace("edge=curl&", "")
            if "http:/" in thumbnail:
                thumbnail = thumbnail.replace("http:/", "https:/")
            try:
                cover_image = image_links['thumbnail']
            except:
                try:
                    cover_image = image_links['smallThumbnail']
                except:
                    cover_image = ""
            if "&edge=curl" in cover_image:
                cover_image = cover_image.replace("&edge=curl", "")
            if "edge=curl&" in cover_image:
                cover_image = cover_image.replace("edge=curl&", "")
            if "http:/" in cover_image:
                cover_image = cover_image.replace("http:/", "https:/")
        except:
            thumbnail = ""
            cover_image = ""
        book_data['thumbnail'] = thumbnail
        book_data['image'] = cover_image
        #render the book sumary page with this information
        return render_template("bookinfo.html", book_data=book_data, user_data=user_book_data)

    # now deal with the case of a book with a google ID
    else:
        urlrequest = 'https://www.googleapis.com/books/v1/volumes/' + book_id + '?key=' + GOOGLE_BOOKS_API_KEY
        try:
            resp = urlopen(urlrequest)
            results = json.load(resp)
        except:
            return render_template("nobook.html")
        #assemble the returned data into a dict
        book_data = {}
        try:
            book_data['title'] = results['volumeInfo']['title']
        except:
            book_data['title'] = ""
        try:
            subtitle = results['volumeInfo']['subtitle']
            if subtitle == "A Novel":
                subtitle = ""
            book_data['subtitle'] = subtitle
        except:
            book_data['subtitle'] = ""
        try:
            format = results['saleInfo']['isEbook']
            if format:
                book_data['format'] = 'Ebook'
            else:
                book_data['format'] = 'Book'
        except:
            book_data['format'] = "Unknown"
        try:
            book_data['year'] = results['volumeInfo']['publishedDate'][0:4]
        except:
            book_data['year'] = ""
        try:
            book_data['descrip'] = results['volumeInfo']['description']
            book_data['descrip'] = Markup(book_data['descrip'])
        except:
            book_data['descrip'] = ""
        book_data['google_id'] = book_id
        try:
            book_data['pages'] = results['volumeInfo']['pageCount']
        except:
            book_data['pages'] = ""
        isbn10= ""
        isbn13 = ""
        try:
            isbns = results['volumeInfo']['industryIdentifiers']
            for item in isbns:
                if item['type'] == 'ISBN_10':
                    isbn10 = item['identifier']
                if item['type'] == 'ISBN_13':
                    isbn13 = item['identifier']
            book_data['isbn10'] = isbn10
            book_data['isbn13'] = isbn13
        except:
            isnb10= ""
            isbn13 = ""
            book_data['isbn10'] = isbn10
            book_data['isbn13'] = isbn13
        try:
            book_data['publisher'] = results['volumeInfo']['publisher']
        except:
            book_data['publisher'] = ""
        try:
            book_data['categories'] = results['volumeInfo']['categories']
        except:
            book_data['categories'] = []
        try:
            book_data['language'] = results['volumeInfo']['language']
        except:
            book_data['language'] = ""
        try:
            thumbnail = results['volumeInfo']['imageLinks']['smallThumbnail']
        except:
            try:
                thumbnail = results['volumeInfo']['imageLinks']['thumbnail']
            except:
                thumbnail = ""
        if "&edge=curl" in thumbnail:
            thumbnail = thumbnail.replace("&edge=curl", "")
        if "edge=curl&" in thumbnail:
            thumbnail = thumbnail.replace("edge=curl&", "")
        if "http:/" in thumbnail:
            thumbnail = thumbnail.replace("http:/", "https:/")
        book_data['thumbnail'] = thumbnail

        try:
            cover_image = results['volumeInfo']['imageLinks']['large']
        except:
            try:
                cover_image = results['volumeInfo']['imageLinks']['extraLarge']
            except:
                try:
                    cover_image = results['volumeInfo']['imageLinks']['medium']
                except:
                    try:
                        cover_image = results['volumeInfo']['imageLinks']['small']
                    except:
                        cover_image = ""
        if "&edge=curl" in cover_image:
            cover_image = cover_image.replace("&edge=curl", "")
        if "edge=curl&" in cover_image:
            cover_image = cover_image.replace("edge=curl&", "")
        if "http:/" in cover_image:
            cover_image = cover_image.replace("http:/", "https:/")
        book_data['image'] = cover_image

        try:
            book_url = results['volumeInfo']['previewLink']
        except:
            try:
                book_url = results['volumeInfo']['infoLink']
            except:
                book_url = ""
        book_data['url'] = book_url

        try:
            authors = results['volumeInfo']['authors']
            n = len(authors)
            authorTuples = []
            for i in range(n):
                author = authors[i]
                author_list = author.split()
                first_name = ' '.join(author_list[:-1])
                last_name = author_list[-1:][0]
                authorTuples.append((last_name, first_name))
            # sort the author tuples into alphabetical order and then assemble them into a string
            authorTuples.sort()
            author_str = ', '.join(' '.join([y, x]) for x, y in authorTuples)
            # add the authors to the book data
            book_data['authors'] = author_str
        except:
            book_data['authors'] = ""
        #render the book sumary page with this information
        return render_template("bookinfo.html", book_data=book_data, user_data=user_book_data)

#display requested default shelf    
@app.route("/defaultshelf", methods=["GET"])
@login_required
def loaddefaultshelf():
    #obtain user's id
    user_id = session["user_id"]
    #ensure that the user has specified a shelf between 1 and 3 - if not redirect to main library
    shelf_number = request.args["shelf"]
    try:
        shelf_number = int(shelf_number)
        if shelf_number < 1 or shelf_number > 3:
            return redirect("/library")
    except:
        return redirect("/library")
    #obtain the book data for the user's In pregress/read/unread books depending on specified shelf
    con = sqlite3.connect('booktree.db')
    con.row_factory = dict_factory
    cur=con.cursor()
    
    if(shelf_number == 1):
        #obtain a list of the user's in progress books
        # this means any books with a positive pages read or in the case of no page data 0 reads
        sqlrequest = "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail, library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE  library.user_id=? AND (books.id IN (SELECT book_id FROM library WHERE user_id=? AND pages_read>0)) OR (books.pages IS NULL AND books.id IN (SELECT book_id FROM library WHERE user_id=? AND nReads=0))"
        rows = cur.execute(sqlrequest, (user_id,user_id,user_id,)).fetchall()
        shelf_name = "In Progress"
    
    if(shelf_number == 2):
        # obtain a list of the user's read books
        sqlrequest = "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail,  library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE  library.user_id=? AND books.id IN (SELECT book_id FROM library WHERE user_id=? AND nReads>0)"
        rows = cur.execute(sqlrequest, (user_id,user_id,)).fetchall()
        shelf_name = "Read"
    
    if(shelf_number == 3):
        # obtain a list of the user's unread books
        sqlrequest = "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail, library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE  library.user_id=? AND books.id IN (SELECT book_id FROM library WHERE user_id=? AND nReads=0)"
        rows = cur.execute(sqlrequest, (user_id,user_id,)).fetchall()
        shelf_name = "Unread"
    
    #obtain the authors for each book
    authorsqlrequest = "SELECT authors.name FROM authors JOIN book_authors ON authors.id = book_authors.author_id JOIN books ON book_authors.book_id=books.id WHERE books.id=?"
    for book in rows:
        author_rows = cur.execute(authorsqlrequest, (book['id'],)).fetchall()
        #assemble a list of tuples where each tuple is a lastname, firstname pair corresponding to one author
        authorTuples = []
        n = len(author_rows)
        for i in range(n):
            author = author_rows[i]['name']
            author_list = author.split()
            first_name = ' '.join(author_list[:-1])
            last_name = author_list[-1:][0]
            authorTuples.append((last_name, first_name))
        # sort the author tuples into alphabetical order and then assemble them into a string
        authorTuples.sort()
        author_str = ', '.join(' '.join([y, x]) for x, y in authorTuples)
        # add the authors to the book data
        book["authors"] = author_str

    con.close()

    return render_template("library.html", books=enumerate(rows), shelf_size=len(rows), shelf_name=shelf_name)

#delete specified cutom shelf
@app.route("/deleteshelf", methods=["POST"])
@login_required
def deleteshelf():
    # delete the given shelf
    shelf_id = request.form['shelf_id']
    user_id = session["user_id"]

    # ensure the specified shelf id is a positive integer
    try:
        shelf_id = int(shelf_id)
        if shelf_id < 1:
            return 'error'
    except:
        return 'error'

    #ensure this shelf belongs to the user:
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    shelf_row = cur.execute("SELECT * FROM user_shelves WHERE shelf_id=? AND user_id=?", (shelf_id, user_id,)).fetchall()
    if len(shelf_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return 'error'
    
    # delete the self from user_shelves, book_shelves, and shelves, tables
    cur.execute("DELETE FROM user_shelves WHERE shelf_id=?", (shelf_id,))
    cur.execute("DELETE FROM book_shelves WHERE shelf_id=?", (shelf_id,))
    cur.execute("DELETE FROM shelves WHERE id=?", (shelf_id,))
    cur.execute("COMMIT")
    #delete the shelf from the user's session
    del session["shelves"][str(shelf_id)]

    con.close()
    return 'success'

#display edit shelves page
@app.route("/editshelves", methods=["GET"])
@login_required
def editshelves():
    return render_template("shelvesEdit.html")

#display the user's library
@app.route("/library", methods=["GET"])
@login_required
def loadlib():
    #obtain user's id
    user_id = session["user_id"]
    #obtain the list data for the user's library books:
    con = sqlite3.connect('booktree.db')
    con.row_factory = dict_factory
    cur=con.cursor()
    #obtain a list of books the user owns
    sqlrequest = "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail, library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE library.user_id=?"
    rows = cur.execute(sqlrequest, (user_id,)).fetchall()

    #obtain the authors for each book
    authorsqlrequest = "SELECT authors.name FROM authors JOIN book_authors ON authors.id = book_authors.author_id JOIN books ON book_authors.book_id=books.id WHERE books.id=?"
    for book in rows:
        author_rows = cur.execute(authorsqlrequest, (book['id'],)).fetchall()
        #assemble a list of tuples where each tuple is a lastname, firstname pair corresponding to one author
        authorTuples = []
        n = len(author_rows)
        for i in range(n):
            author = author_rows[i]['name']
            author_list = author.split()
            first_name = ' '.join(author_list[:-1])
            last_name = author_list[-1:][0]
            authorTuples.append((last_name, first_name))
        # sort the author tuples into alphabetical order and then assemble them into a string
        authorTuples.sort()
        author_str = ', '.join(' '.join([y, x]) for x, y in authorTuples)
        # add the authors to the book data
        book["authors"] = author_str

    con.close()

    return render_template("library.html", books=enumerate(rows), shelf_size=len(rows), shelf_name="My Library")

#GET - display login page
#POST - log the user in
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        # display log in form
        return render_template("login.html")
    else:
        # ensure non empty email submitted:
        email = request.form.get("email")
        try:
            email = email.strip().lower()
            if not email:
                flash('All fields must be populated', 'error')
                return redirect("/login")
        except:
            flash('All fields must be populated', 'error')
            return redirect("/login")

        # ensure non-empty pw submitted
        pw = request.form.get("password")
        if not pw:
            flash('All fields must be populated', 'error')
            return redirect("/login")

        # check email is registered
        con = sqlite3.connect('booktree.db')
        con.isolation_level = None
        con.row_factory = dict_factory
        cur=con.cursor()
        while True:
            try:
                cur.execute("BEGIN IMMEDIATE")
                break
            except:
                pass
        row=cur.execute("SELECT * FROM users WHERE email=?", (email,))
        row = row.fetchall()
        if len(row) == 0:
            cur.execute("COMMIT")
            flash('Email is not registered', 'error')
            con.close()
            return redirect("/login")

        # check password correct
        hash = row[0]["hash"]
        if not sha256_crypt.verify(pw, hash):
            cur.execute("COMMIT")
            flash('Password incorrect', 'error')
            con.close()
            return redirect("/login")
        
        # Log the user in
        session.clear()
        session["user_id"] = row[0]["id"]
        user_id = row[0]["id"]
        session["user_name"] = row[0]["name"]

        # add the user's shelves to the session
        session["shelves"] = {}
        shelf_names = cur.execute("SELECT id, shelf FROM shelves WHERE id IN (SELECT shelf_id FROM user_shelves WHERE user_id=?) ORDER BY shelf", (user_id,)).fetchall()
        for shelf in shelf_names:
            session["shelves"][str(shelf['id'])] = shelf['shelf']
        cur.execute("COMMIT")
        con.close()
        flash('Log in successful', 'success')
        return redirect("/")

#log the user out and return to homepage
@app.route("/logout")
def logout():
    session.clear()
    flash('Logged Out', 'success')
    return redirect("/")

#query the google/ISBN API with search terms and return book results
@app.route("/query", methods=["POST"])
@login_required
def query():
    # get isbn and book description from form
    isbn = request.form.get("isbn")
    descrip = request.form.get("desc")
    # if nothin input, return an empty list json
    try:
        isbn = isbn.strip()
        #must also remove all non-numeric data (e.g "ISBN", spaces, - etc) for google search:
        numeric_isbn = re.sub(r'[^0-9]+', '', isbn)
        descrip = descrip.strip()
        if not isbn and not descrip:
            return jsonify([])
    except:
        return jsonify([])
    # if they have given an isbn, search this first
    if len(numeric_isbn)>0:
        #request book from google:
        google_request_url = 'https://www.googleapis.com/books/v1/volumes?q=' + numeric_isbn + '+isbn:' + numeric_isbn + '&maxResults=40&printType=books&key=' + GOOGLE_BOOKS_API_KEY
        resp = urlopen(google_request_url)
        book_data = json.load(resp)
        # if the search returns 1 or more books, assemble necessary info into a dictionary
        # evaluate for each of the results which are already in library/wishlist and return as a JSON
        if(book_data["totalItems"] > 0):
            book_results = google_results_to_list(book_data)
            book_results = stock_check(book_results)
            return jsonify(book_results)
        # if google cannot  find the isbn try isbnlib
        if(book_data["totalItems"] == 0):
            # first test whether it is a valid ISBN
            if is_isbn10(numeric_isbn) or is_isbn13(numeric_isbn):
                #start by searching via wiki
                try:
                    book_data = meta(numeric_isbn)
                except:
                    book_data = {}
                #if a book is returned, return these results
                # (first transforming into a canonical dictionary and checking whether already present in library/wishlist)
                if(len(book_data.keys()) > 0):
                    book_results = isbn_results_to_list(book_data, numeric_isbn, 'wiki')
                    book_results = stock_check(book_results)
                    return jsonify(book_results)
                #if we still have no results, search isbn via open library
                else:
                    try:
                        book_data = meta(numeric_isbn, 'openl')
                    except:
                        book_data = {}
                    #if a book is returned, return these results
                    # (first transforming into a canonical dictionary and checking whether already present in library/wishlist)
                    if(len(book_data.keys()) > 0):
                        book_results = isbn_results_to_list(book_data, numeric_isbn, 'openl')
                        book_results = stock_check(book_results)
                        return jsonify(book_results)
                    #if we still have no results, return a generic google search for the isbn (if this has any results)
                    #(first transforming into a canonical dictionary and checking whether already present in library/wishlist)
                    else:
                        google_request_url = 'https://www.googleapis.com/books/v1/volumes?q=' + numeric_isbn + '&maxResults=40&printType=books&key=' + GOOGLE_BOOKS_API_KEY
                        resp = urlopen(google_request_url)
                        book_data = json.load(resp)
                        if(book_data["totalItems"] > 0):
                            book_results = google_results_to_list(book_data)
                            book_results = stock_check(book_results)
                            return jsonify(book_results)

    # no valid isbn, try the description
    # empty description, return nothing
    if len(descrip) == 0:
        return jsonify([])
    
    # search google for the book
    #getting rid of punctuation
    alphanumeric_search = re.sub(r'[^A-Za-z0-9 ]+', '', descrip)
    #separate search terms into array of words, 
    search_words = alphanumeric_search.split()
    #assemple url from search terms
    google_request_url = 'https://www.googleapis.com/books/v1/volumes?q=' 
    n = len(search_words)
    for i in range(n):
        google_request_url += search_words[i]
        if i < (n-1):
            google_request_url += '+'
    google_request_url += '&maxResults=40&printType=books&key=' + GOOGLE_BOOKS_API_KEY
    resp = urlopen(google_request_url)
    book_data = json.load(resp)

    # if results returned, convert into canonical dictionary and return as JSOn, else return empty list
    if(len(book_data["items"]) > 0):
        book_results = google_results_to_list(book_data)
        book_results = stock_check(book_results)
        return jsonify(book_results)
    else:
        return jsonify([])

#GET - display registration form
#POST - register a new user
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        # display registration form
        return render_template("register.html")
    else:
        # ensure a non empty name was submitted
        name = request.form.get("name")
        try:
            name = name.strip()
            if not name:
                flash('All fields must be populated', 'error')
                return redirect("/register")
        except:
            flash('All fields must be populated', 'error')
            return redirect("/register")
        
        # ensure non empty email submitted:
        email = request.form.get("email")
        try:
            email = email.strip().lower()
            if not email:
                flash('All fields must be populated', 'error')
                return redirect("/register")
        except:
            flash('All fields must be populated', 'error')
            return redirect("/register")

        #ensure length 8-20 pw submitted and that the retype matches
        pw = request.form.get("password")
        conf = request.form.get("confirmation")
        if not pw or not conf:
            flash('All fields must be populated', 'error')
            return redirect("/register")
        if (len(pw) < 8) or (len(pw) > 20):
            flash('Passwords must be between 8 and 20 characters', 'error')
            return redirect("/register")
        if conf != pw:
            flash('Passwords did not match', 'error')
            return redirect("/register")

        # check email not already used
        con = sqlite3.connect('booktree.db')
        con.isolation_level = None
        con.row_factory = dict_factory
        cur=con.cursor()
        while True:
            try:
                cur.execute("BEGIN IMMEDIATE")
                break
            except:
                pass
        rows=cur.execute("SELECT * FROM users WHERE email=?", (email,))
        if len(rows.fetchall()) > 0:
            cur.execute("COMMIT")
            flash('This email is already registered', 'error')
            con.close()
            return redirect("/register")

        # if successful submission, add user to database, log them in and redirect to title page
        cur.execute("INSERT INTO users (name, email, hash) VALUES (?, ?, ?)", (name, email, sha256_crypt.hash(pw),))
        row = cur.execute("SELECT * FROM users WHERE email=?", (email,))
        row = row.fetchall()
        user_id=row[0]["id"]
        cur.execute("COMMIT")
        con.close()

        session.clear()
        session["user_id"] = user_id
        session["user_name"] = row[0]["name"]
        session["shelves"] = {}

        flash('Registration Successful', 'success')
        return redirect("/")

#remove the specified book from the user's library
@app.route("/removeFromLib", methods=["POST"])
@login_required
def removefromlib():
    # get id from button clicked
    button_id = request.form.get("id")
    # if this is an ISBN we must remove the suffix (if present)
    if button_id[0:4] == 'ISBN':
        if button_id[-5:] == 'openl':
            book_tag = button_id[:-5]
        elif button_id[-4:] == 'wiki':
            book_tag = button_id[:-4]
        else:
            book_tag = button_id
    #otherwise the button id gives us the google id
    else:
        book_tag = button_id
    # get the user's id:
    user_id = session["user_id"]
    #now search the DB to see if this book exists and get it's ID
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    row = cur.execute("SELECT id FROM books WHERE google_id=?", (book_tag,)).fetchall()
    # if no id is returned then the book is not present and there is nothing to remove
    if len(row) == 0:
        cur.execute("COMMIT")
        con.close()
        return 'Failure'
    # get the book_id and remove the relevant from from the user's library
    book_id = row[0]['id']
    cur.execute("DELETE FROM library WHERE user_id=? AND book_id=?", (user_id,book_id,))
    # if this book is any of this user's shelves remove it
    cur.execute("DELETE FROM book_shelves WHERE book_id=? AND shelf_id IN (SELECT shelf_id FROM user_shelves WHERE user_id=?)", (book_id,user_id,))
    cur.execute("COMMIT")
    con.close()
    return 'Success'

#remove the specified book from a custom shelf
@app.route("/removeFromShelf", methods=["POST"])
@login_required
def removeFromShelf():
    # delete the specified book from the given shelf
    shelf_id = request.form['shelf_id']
    book_tag = request.form['book_id']
    user_id = session["user_id"]

    # ensure the specified shelf id is a positive integer
    try:
        shelf_id = int(shelf_id)
        if shelf_id < 1:
            return 'error'
    except:
        return 'error'
    
    #ensure that a book_tag is specified
    if not book_tag:
        return 'error'

    #ensure this shelf belongs to the user:
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    shelf_row = cur.execute("SELECT * FROM user_shelves WHERE shelf_id=? AND user_id=?", (shelf_id, user_id,)).fetchall()
    if len(shelf_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return 'error'

    #delete specified book if it is on this shelf
    #first get the book_id
    book_id = cur.execute("SELECT id FROM books WHERE google_id=?", (book_tag,)).fetchall()
    if len(book_id) == 0:
            cur.execute("COMMIT")
            con.close()
            return 'error'
    book_id = book_id[0]['id']

    cur.execute("DELETE FROM book_shelves WHERE book_id=? AND shelf_id=?", (book_id,shelf_id,))
    cur.execute("COMMIT")
    con.close()
    return 'success'

#remove the specified book from the user's wishlist
@app.route("/removeFromWish", methods=["POST"])
@login_required
def removefromwish():
    # get id from button clicked
    button_id = request.form.get("id")
    # if this is an ISBN we must remove the suffix (if present)
    if button_id[0:4] == 'ISBN':
        if button_id[-5:] == 'openl':
            book_tag = button_id[:-5]
        elif button_id[-4:] == 'wiki':
            book_tag = button_id[:-4]
        else:
            book_tag = button_id
    #otherwise the button id gives us the google id
    else:
        book_tag = button_id
    # get the user's id:
    user_id = session["user_id"]
    #now search the DB to see if this book exists and get it's ID
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    row = cur.execute("SELECT id FROM books WHERE google_id=?", (book_tag,)).fetchall()
    # if no id is returned then the book is not present and there is nothing to remove
    if len(row) == 0:
        cur.execute("COMMIT")
        con.close()
        return 'Failure'
    # get the book_id and remove the relevant from from the user's library
    book_id = row[0]['id']
    cur.execute("DELETE FROM wishlist WHERE user_id=? AND book_id=?", (user_id,book_id,))
    cur.execute("COMMIT")
    con.close()
    return 'Success'

# rename a custom shelf
@app.route("/renameshelf", methods=["POST"])
@login_required
def renameshelf():
    # rename the given shelf
    shelf_id = request.form['shelf_id']
    shelf_name = request.form['shelf_name']
    user_id = session["user_id"]

    # ensure the specified shelf id is a positive integer
    try:
        shelf_id = int(shelf_id)
        if shelf_id < 1:
            return 'error'
    except:
        return 'error'

    #ensure that the name is non-empty
    try:
        shelf_name = shelf_name.strip().title()
        if not shelf_name:
            return 'empty'
    except:
        return 'error'

    #ensure this shelf belongs to the user:
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    shelf_row = cur.execute("SELECT * FROM user_shelves WHERE shelf_id=? AND user_id=?", (shelf_id, user_id,)).fetchall()
    if len(shelf_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return 'error'
    
    #ensure that the user doesn't already have a shelf with this name
    shelf_row = cur.execute("SELECT id FROM shelves WHERE shelf=? AND id IN (SELECT shelf_id FROM user_shelves WHERE user_id=?)", (shelf_name, user_id,)).fetchall()
    if len(shelf_row) > 0:
        cur.execute("COMMIT")
        return 'repeat'
    
    # rename the shelf
    cur.execute("UPDATE shelves SET shelf=? WHERE id=?", (shelf_name,shelf_id,))
    cur.execute("COMMIT")
    #rename the shelf in the user's session
    session["shelves"][str(shelf_id)] = shelf_name

    con.close()
    return 'success'

#display book search page
@app.route("/search", methods=["GET"])
@login_required
def search():
    if request.method == "GET":
        # display search form
        return render_template("search.html")

# sort (as specified), search (as specified), and return the books on the given shelf
@app.route("/sortAndSearchBooks", methods=["POST"])
@login_required
def sortAndSearchBooks():
    #first obtain the user's sorting method, search term, search method, shelf, and id
    user_id = session["user_id"]
    sort = request.form["sort"]
    shelf = request.form["shelf"]
    search_term = request.form["search_term"]
    search_method = request.form["search_method"]

    # ensure a valid sort option is selected and identify the correct SQL command
    # author sorting wil be slightly more convoluted and so does not have a single command
    sqlsort = { "az-author" : "ORDER BY title, subtitle", "az-title" : "ORDER BY title, subtitle", "date-added" : "ORDER BY date_added DESC", "date-moded" : "ORDER BY date_modified DESC", "rating" : "ORDER BY rating DESC, title, subtitle"}
    try:
        sqlsortcommand = sqlsort[sort]
    except:
        return jsonify([])
    
    # ensure that if wishlist is specified, a valid sort selection is chosen:
    if shelf == "wishl" and sort in ["date-moded", "rating"]:
        return jsonify([])

    # if a search term is specified, ensure there is a valid search method
    if search_term:
        search_term = search_term.strip().lower()
        # if an invalid search method has been entered, or only whitespace is searched for, return no resutls
        if not search_method in ["title-search", "author-search"] or not search_term:
            return jsonify([])
        # title search can be done via sql search command, author search must be done on returned results:
        if search_method == "title-search":
            sqlsearchcommand = "AND ((title LIKE '%" + search_term + "%') OR (subtitle LIKE '%" + search_term + "%'))"
        else:
            sqlsearchcommand = ""
    else:
        sqlsearchcommand = ""
    
    # ensurea valid shelf has been specified - either all, in progress, read, unread, or an integer cutom shelf
    if not shelf in ["all", "in-progress",  "read", "unread", "wishl"]:
        try:
            shelf = int(shelf)
            if shelf < 1:
                return jsonify([])
        except:
            return jsonify([])

    

    con = sqlite3.connect('booktree.db')
    con.row_factory = dict_factory
    cur=con.cursor()
    
    # First we deal with the case of the default bookshelves:
    if shelf in ["all", "in-progress",  "read", "unread", "wishl"]:
        # determine the correct book select command
        sqlselect = {"all" : "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail, library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE library.user_id=?",
        "in-progress" : "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail, library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE library.user_id=? AND (books.id IN (SELECT book_id FROM library WHERE user_id=? AND pages_read>0)) OR (books.pages IS NULL AND books.id IN (SELECT book_id FROM library WHERE user_id=? AND nReads=0))",
        "read" : "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail, library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE library.user_id=? AND books.id IN (SELECT book_id FROM library WHERE user_id=? AND nReads>0)",
        "unread" : "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail, library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE library.user_id=? AND books.id IN (SELECT book_id FROM library WHERE user_id=? AND nReads=0)",
        "wishl" : "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail FROM books JOIN format ON books.format_id = format.id JOIN wishlist ON books.id=wishlist.book_id WHERE wishlist.user_id=?"}

        sqlselectcommand = sqlselect[shelf]
        sqlcommand = sqlselectcommand + sqlsearchcommand + sqlsortcommand

        #obtain the sorted list of books
        if shelf == "in-progress":
            rows = cur.execute(sqlcommand, (user_id,user_id,user_id,)).fetchall()
        elif shelf in ["all", "wishl"]:
            rows = cur.execute(sqlcommand, (user_id,)).fetchall()
        else:
            rows = cur.execute(sqlcommand, (user_id,user_id,)).fetchall()
    else:
        #in the case of custom bookshelves, we must first determine whether the user owns this shelf
        row = cur.execute("SELECT * FROM user_shelves WHERE user_id=? AND shelf_id=?", (user_id, shelf,)).fetchall()
        if len(row) == 0:
            con.close()
            return jsonify([])
        
        #if the user owns this shelf, obtain the sorted shelf book data
        sqlselectcommand = "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail, library.rating FROM books JOIN format ON books.format_id = format.id JOIN library ON books.id=library.book_id WHERE library.user_id=? AND books.id IN (SELECT book_id FROM book_shelves WHERE shelf_id=?)"
        
        sqlcommand = sqlselectcommand + sqlsearchcommand + sqlsortcommand
        rows = cur.execute(sqlcommand, (user_id,shelf,)).fetchall()

    #obtain the authors for each book
    authorsqlrequest = "SELECT authors.name FROM authors JOIN book_authors ON authors.id = book_authors.author_id JOIN books ON book_authors.book_id=books.id WHERE books.id=?"
    for book in rows:
        author_rows = cur.execute(authorsqlrequest, (book['id'],)).fetchall()
        #assemble a list of tuples where each tuple is a lastname, firstname pair corresponding to one author
        authorTuples = []
        n = len(author_rows)
        for i in range(n):
            author = author_rows[i]['name']
            author_list = author.split()
            first_name = ' '.join(author_list[:-1])
            last_name = author_list[-1:][0]
            authorTuples.append((last_name, first_name))
        # sort the author tuples into alphabetical order and then assemble them into a string
        authorTuples.sort()
        author_str = ', '.join(' '.join([y, x]) for x, y in authorTuples)
        # add the authors to the book data
        book["authors"] = author_str
        # now assemble the sorted list of authors into 1 tuple, arranged lastname, firstname, last name, first name, etc in alphabetical author order
        # add this tuple to the book - for sorting alphabetically by author
        totalAuthorTuple = ()
        for name in authorTuples:
            totalAuthorTuple += name
        book["author_tuple"] = totalAuthorTuple
        
    #if we are sorting by author, then sort the books according to author_tuple
    if sort == "az-author":
        rows = sorted(rows, key = lambda book: book['author_tuple'])
    
    #if we are searching by author, extract the books which match our search term
    if search_term and search_method == "author-search":
        rows = [book for book in rows if any(word in book["authors"].lower() for word in search_term.split())]
            
    con.close()
    return jsonify(rows)

# add submitted notes to the user's library record for given book
@app.route("/updateNotes", methods=["POST"])
@login_required
def updateNotes():
    # first get the notes and book ID and user ID
    notes = request.form["book-notes"]
    booktag = request.form["booktag"]
    user_id = session["user_id"]

    #ensure that the book exists and is owned by the user
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    book_row = cur.execute("SELECT id FROM books WHERE google_id=?", (booktag,)).fetchall()
    if len(book_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return 'Failed'
    book_id = book_row[0]["id"]

    lib_row = cur.execute("SELECT * FROM library WHERE user_id=? AND book_id=?", (user_id,book_id,)).fetchall()
    if len(lib_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return 'Failed'
    
    # if the iinputs are valid, update the users notes and the date modified
    cur.execute("UPDATE library SET notes=?, date_modified=? WHERE user_id=? AND book_id=?", (notes, datetime.now(), user_id, book_id,))
    cur.execute("COMMIT")
    con.close()

    return ('', http.HTTPStatus.NO_CONTENT)

# update a user's pages read for a given book
@app.route("/updateProgress", methods=["POST"])
@login_required
def updateProgress():
    # get the user id, book id, and number of pages we want to update
    booktag = request.form["id"]
    pages = request.form["pages"]
    user_id = session["user_id"]
    
    # ensure that the input pages is a positive integer
    try:
        pages = int(pages)
        if pages < 0:
            return 'Failed'
    except:
        return 'Failed'
    
    # ensure that the book exists in our database and that it has a number of pages greater than the input #read pages
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    book_row = cur.execute("SELECT id, pages FROM books WHERE google_id=?", (booktag,)).fetchall()
    if len(book_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return 'Failed'
    if not book_row[0]["pages"] or pages > book_row[0]["pages"]:
        cur.execute("COMMIT")
        con.close()
        return 'Failed'

    # ensure that the book is owned by the user
    lib_row = cur.execute("SELECT * FROM library WHERE user_id=? AND book_id=?", (user_id,book_row[0]["id"],)).fetchall()
    if len(lib_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return 'Failed'
    
    # if the inputs are valid, update the pages read and date modified for the entry
    cur.execute("UPDATE library SET pages_read=?, date_modified=? WHERE user_id=? AND book_id=?", (pages, datetime.now(), user_id, book_row[0]["id"],))
    cur.execute("COMMIT")
    con.close()
    return 'Success'

# update the "in progress" status for a given book
@app.route("/updateProgressStatus", methods=["POST"])
@login_required
def updateProgressStatus():
    # get the user id, book id, and status we want to update
    booktag = request.form["id"]
    status = request.form["in_progress"]
    user_id = session["user_id"]
    
    # check that the status is either 0 or 1
    try:
        status = int(status)
        if status < 0 or status > 1:
            return ('', http.HTTPStatus.BAD_REQUEST)
    except:
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    #check that the user owns the specified book
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    book_row = cur.execute("SELECT id FROM books WHERE google_id=?", (booktag,)).fetchall()
    if len(book_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    lib_row = cur.execute("SELECT * FROM library WHERE user_id=? AND book_id=?", (user_id,book_row[0]["id"],)).fetchall()
    if len(lib_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    #if the user owns the book, update status and time modified
    cur.execute("UPDATE library SET in_progress=?, date_modified=? WHERE user_id=? AND book_id=?", (status, datetime.now(), user_id, book_row[0]["id"],))
    cur.execute("COMMIT")
    con.close()
    return ('', http.HTTPStatus.NO_CONTENT)

# update a user's book rating
@app.route("/updateRating", methods=["POST"])
@login_required
def updateRating():
    # get the user id, book id, and rating we want to update
    booktag = request.form["booktag"]
    rating = request.form["star"]
    user_id = session["user_id"]

    #check that the returned rating is an integer betwween 1 and 5
    try:
        rating = int(rating)
    except:
        return ('', http.HTTPStatus.BAD_REQUEST)
    if rating < 1 or rating > 5:
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    #check that the user owns the specified book
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    book_row = cur.execute("SELECT id FROM books WHERE google_id=?", (booktag,)).fetchall()
    if len(book_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    lib_row = cur.execute("SELECT * FROM library WHERE user_id=? AND book_id=?", (user_id,book_row[0]["id"],)).fetchall()
    if len(lib_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return ('', http.HTTPStatus.BAD_REQUEST)

    #if the user owns the book, update rating
    cur.execute("UPDATE library SET rating=?, date_modified=? WHERE user_id=? AND book_id=?", (rating, datetime.now(), user_id, book_row[0]["id"],))
    cur.execute("COMMIT")
    con.close()
    return ('', http.HTTPStatus.NO_CONTENT)

# update the user's number of reads of a given book
@app.route("/updateReads", methods=["POST"])
@login_required
def updateReads():
    # get the user id, book id, and number we want to update
    booktag = request.form["id"]
    reads = request.form["reads"]
    user_id = session["user_id"]

    # check that it is a positive integer number 
    try:
        reads = int(reads)
    except:
        return ('', http.HTTPStatus.BAD_REQUEST)
    if reads < 0:
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    #check that the user owns the given book
    #check that the user owns the specified book
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    book_row = cur.execute("SELECT id FROM books WHERE google_id=?", (booktag,)).fetchall()
    if len(book_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return ('', http.HTTPStatus.BAD_REQUEST)
    
    lib_row = cur.execute("SELECT * FROM library WHERE user_id=? AND book_id=?", (user_id,book_row[0]["id"],)).fetchall()
    if len(lib_row) == 0:
        cur.execute("COMMIT")
        con.close()
        return ('', http.HTTPStatus.BAD_REQUEST)

    #if the user owns the book, update number of reads and time modified 
    cur.execute("UPDATE library SET nReads=?, date_modified=? WHERE user_id=? AND book_id=?", (reads, datetime.now(), user_id, book_row[0]["id"],))
    cur.execute("COMMIT")
    con.close()
    return ('', http.HTTPStatus.NO_CONTENT)

#display the user's wishlist
@app.route("/wishlist", methods=["GET"])
@login_required
def loadwishes():
    #obtain user's id
    user_id = session["user_id"]
    #obtain the list data for the user's library books:
    con = sqlite3.connect('booktree.db')
    con.row_factory = dict_factory
    cur=con.cursor()
    #obtain a list of books the user added to their wishlist
    sqlrequest =  "SELECT books.id, google_id, title, subtitle, year, format.format, thumbnail FROM books JOIN format ON books.format_id = format.id JOIN wishlist ON books.id=wishlist.book_id WHERE wishlist.user_id=?"
    rows = cur.execute(sqlrequest, (user_id,)).fetchall()
    #obtain the authors for each book
    authorsqlrequest = "SELECT authors.name FROM authors JOIN book_authors ON authors.id = book_authors.author_id JOIN books ON book_authors.book_id=books.id WHERE books.id=?"
    for book in rows:
        author_rows = cur.execute(authorsqlrequest, (book['id'],)).fetchall()
        #assemble a list of tuples where each tuple is a lastname, firstname pair corresponding to one author
        authorTuples = []
        n = len(author_rows)
        for i in range(n):
            author = author_rows[i]['name']
            author_list = author.split()
            first_name = ' '.join(author_list[:-1])
            last_name = author_list[-1:][0]
            authorTuples.append((last_name, first_name))
        # sort the author tuples into alphabetical order and then assemble them into a string
        authorTuples.sort()
        author_str = ', '.join(' '.join([y, x]) for x, y in authorTuples)
        # add the authors to the book data
        book["authors"] = author_str

    con.close()

    return render_template("wishlist.html", books=enumerate(rows), shelf_size=len(rows))

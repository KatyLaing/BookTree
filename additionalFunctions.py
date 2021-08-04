import json
import os
import sqlite3

from flask import redirect, session
from functools import wraps
from isbnlib import cover, meta
from urllib.request import urlopen

GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API")

#function used to dictate how sql commands return table rows to python
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

#given a google id, add the book to our database and return the book_id
def add_book_to_db(gid):
    # obtain the book data from google
    urlrequest = 'https://www.googleapis.com/books/v1/volumes/' + gid + '?key=' + GOOGLE_BOOKS_API_KEY
    try:
        resp = urlopen(urlrequest)
        book_data = json.load(resp)
    except:
        return 0
    # obtain a list of authors
    try:
        authors = book_data['volumeInfo']['authors']
    except:
        authors = []
    #add authors to DB (without redundancies) and record their author ids:
    author_ids = add_data_to_table(authors, "authors", "name")

    # extract publishers
    try:
        publisher = [book_data['volumeInfo']['publisher']]
    except:
        publisher = []
    #add publisher to DB (without redundancies) and record the publisher ids:
    pub_ids = add_data_to_table(publisher, "publisher", "publisher")

    #extract the categories:
    try:
        categories = book_data['volumeInfo']['categories']
    except:
        categories = []
    #add categories to DB (without redundancies) and record the cat ids:
    cat_ids = add_data_to_table(categories, "categories", "category")

    #extract the language:
    try:
        language = [book_data['volumeInfo']['language']]
    except:
        language = []
    #add language to DB (without redundancies) and record the language id:
    lang_ids = add_data_to_table(language, "languages", "language")

    #now all foreign keys are known, we can insert the remaining book data directly into the books db:
    # extract title:
    try:
        title = book_data['volumeInfo']['title']
    except:
        title = ""
    # extract subtitle:
    try:
        subtitle = book_data['volumeInfo']['subtitle']
        if subtitle == "A Novel":
            subtitle = ""
    except:
        subtitle = ""
    #extract publishing year:
    try:
        yr = book_data['volumeInfo']['publishedDate'][0:4]
    except:
        yr = None
    #extract book description
    try:
        descrip = book_data['volumeInfo']['description']
    except:
        descrip = ''
    #extract number of pages
    try:
        nPages = book_data['volumeInfo']['pageCount']
    except:
        nPages = None
    #extract isbn10 and 13
    try:
        isbn10 = ""
        isbn13 = ""
        isbns = book_data['volumeInfo']['industryIdentifiers']
        for entry in isbns:
            if entry['type'] == "ISBN 10":
                isbn10 = entry['identifier']
            if entry['type'] == "ISBN 13":
                isbn13 = entry['identifier']
    except:
        isbn10 = ""
        isbn13 = ""
    #extract a thumbnail and a larger image of the cover:
    try:
        thumbnail = book_data['volumeInfo']['imageLinks']['smallThumbnail']
    except:
        try:
            thumbnail = book_data['volumeInfo']['imageLinks']['thumbnail']
        except:
            thumbnail = ""
    if "&edge=curl" in thumbnail:
        thumbnail = thumbnail.replace("&edge=curl", "")
    if "edge=curl&" in thumbnail:
        thumbnail = thumbnail.replace("edge=curl&", "")
    if "http:/" in thumbnail:
            thumbnail = thumbnail.replace("http:/", "https:/")
    
    try:
        cover_image = book_data['volumeInfo']['imageLinks']['large']
    except:
        try:
            cover_image = book_data['volumeInfo']['imageLinks']['extraLarge']
        except:
            try:
                cover_image = book_data['volumeInfo']['imageLinks']['medium']
            except:
                try:
                    cover_image = book_data['volumeInfo']['imageLinks']['small']
                except:
                    cover_image = ""
    if "&edge=curl" in cover_image:
        cover_image = cover_image.replace("&edge=curl", "")
    if "edge=curl&" in cover_image:
        cover_image = cover_image.replace("edge=curl&", "")
    if "http:/" in cover_image:
            cover_image = cover_image.replace("http:/", "https:/")
    
    #extract book URL:
    try:
        book_url = book_data['volumeInfo']['previewLink']
    except:
        try:
            book_url = book_data['volumeInfo']['infoLink']
        except:
            book_url = ""
    
    # determine the correct format id
    try:
        format = ''
        if(book_data['saleInfo']['isEbook'] == True):
            format = 'Ebook'
        if(book_data['saleInfo']['isEbook'] == False):
            format = 'Book'
    except:
        format = 'Unknown'
    
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    format_id = cur.execute("SELECT * FROM format WHERE format=?", (format,)).fetchall()[0]['id']

    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    
    #ensure the book is not already in DB
    rows = cur.execute("SELECT id FROM books WHERE google_id=?", (gid,)).fetchall()
    if len(rows) == 0:
        #now insert all of the book data into the DB:
        sqlcommand = "INSERT INTO books (title, subtitle, year, format_id, descrip, google_id, pages, pub_id, isbn10, isbn13, thumbnail, image, lang_id, url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        cur.execute(sqlcommand, (title, subtitle, yr, format_id, descrip, gid, nPages, pub_ids[0], isbn10, isbn13, thumbnail, cover_image, lang_ids[0], book_url,))

        #obtain the book id:
        book_id = cur.execute("SELECT id FROM books WHERE google_id=?",  (gid,)).fetchall()[0]['id']
        #now link the book to its authors/categories in the relevant tables:
        #if the book has valid author ids insert  the links into the book_authors table
        if not ((len(author_ids) == 1) and (author_ids[0] == 0)):
            unique_authors = set(author_ids)
            for id in unique_authors:
                cur.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?,?)", (book_id, id,))
        
        #if the book has valid category ids insert  the links into the book_cats table
        if not ((len(cat_ids) == 1) and (cat_ids[0] == 0)):
            unique_cats = set(cat_ids)
            for id in unique_cats:
                cur.execute("INSERT INTO book_categories (book_id, cat_id) VALUES (?,?)", (book_id, id,))

    cur.execute("COMMIT")
    con.close()
    return book_id

#function that takes a list of values, adds them to given table in specified field (this is a basic table with only 1 data column and id) without redundancies
# returns the list of ids assocuated with the values
def add_data_to_table(values, table, field_name):
    ids = []
    # if no values, we use id 0:
    if len(values) == 0:
        ids.append(0)
    else:
    # otherwise, add all values to DB if not already present and record the ids
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
        for value in values:
            #determine if value already in DB:
            command = "SELECT * FROM " + table + " WHERE " + field_name + "=?"
            rows=cur.execute(command, (value,))
            rows = rows.fetchall()
            #if the value is already in the database, record the id
            if len(rows) == 1:
                ids.append(rows[0]['id'])
            # if value not yet in the db, add them and record id
            if len(rows) == 0:
                command = "INSERT INTO " + table + " (" + field_name + ") VALUES (?)"
                cur.execute(command, (value,))
                command = "SELECT * FROM " + table + " WHERE " + field_name + "=?"
                rows=cur.execute(command, (value,))
                rows = rows.fetchall()
                ids.append(rows[0]['id'])
        cur.execute("COMMIT")
        con.close()
    return ids

# add book to DB in the ISBN case and return the book_id
def add_isbn_to_db(id, suffix):
    # obtain book data:
    if suffix == 'unknown':
        try:
            book_data = meta(id, 'wiki')
            if len(book_data.keys()) == 0:
                try:
                    book_data = meta(id, 'openl')
                except:
                    return 0
        except:
            try:
                book_data = meta(id, 'openl')
            except:
                return 0
    else:
        try:
            book_data = meta(id, suffix)
        except:
            return 0
    if len(book_data.keys()) == 0:
        return 0
    #obtain list of authors
    try:
        authors = book_data['Authors']
    except:
        authors = []
    #add authors to DB (without redundancies) and record their author ids:
    author_ids = add_data_to_table(authors, "authors", "name")

    # extract publishers
    try:
        if book_data['Publisher'] == '':
            publisher = []
        else:
            publisher = [book_data['Publisher']]
    except:
        publisher = []
    #add publisher to DB (without redundancies) and record the publisher ids:
    pub_ids = add_data_to_table(publisher, "publisher", "publisher")

    #extract the language:
    try:
        if book_data['Language'] == '':
            language = []
        else:
            language = [book_data['Language']]
    except:
        language = []
    #add language to DB (without redundancies) and record the language id:
    lang_ids = add_data_to_table(language, "languages", "language")

    #now all foreign keys are known, we can insert the remaining book data directly into the books db:
    # extract title:
    try:
        title = book_data['Title']
    except:
        title = ""
    try:
        subtitle = book_data['Subitle']
    except:
        subtitle = ""
    #extract publishing year:
    try:
        if book_data['Year'] == '':
            yr = None
        else:
            yr = book_data['Year'][0:4]
    except:
        yr = None
    # no description from isbn
    descrip = ''
    # no pagenumber from isbn
    nPages = None
    #extract isbn10 and 13
    try:
        isbn10 = book_data['ISBN-10']
    except:
        isbn10 = ""
    try:
        isbn13 = book_data['ISBN-13']
    except:
        isbn13 = ""
    #extract a thumbnail and a larger image of the cover:
    try:
        image_links = cover(id)
        try:
            small = image_links['smallThumbnail']
            thumbnail = small
        except:
            try:
                large = image_links['thumbnail']
                thumbnail = large
            except:
                thumbnail = ""
        if "&edge=curl" in thumbnail:
            thumbnail = thumbnail.replace("&edge=curl", "")
        if "edge=curl&" in thumbnail:
            thumbnail = thumbnail.replace("edge=curl&", "")
        if "http:/" in thumbnail:
            thumbnail = thumbnail.replace("http:/", "https:/")
        try:
            large = image_links['thumbnail']
            cover_image = large
        except:
            try:
                small = image_links['smallThumbnail']
                cover_image = small
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
    
    #no url from isbn
    book_url = ""

    #set format id
    con = sqlite3.connect('booktree.db')
    con.isolation_level = None
    con.row_factory = dict_factory
    cur=con.cursor()
    format = 'Unknown'
    format_id = cur.execute("SELECT * FROM format WHERE format=?", (format,)).fetchall()[0]['id']

    while True:
        try:
            cur.execute("BEGIN IMMEDIATE")
            break
        except:
            pass
    
    #check that the book is not already in the lib
    rows = cur.execute("SELECT id FROM books WHERE google_id=?", (id,)).fetchall()
    if len(rows) == 0:
        #now insert all of the book data into the DB:
        sqlcommand = "INSERT INTO books (title, subtitle, year, format_id, descrip, google_id, pages, pub_id, isbn10, isbn13, thumbnail, image, lang_id, url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        cur.execute(sqlcommand, (title, subtitle, yr, format_id, descrip, id, nPages, pub_ids[0], isbn10, isbn13, thumbnail, cover_image, lang_ids[0], book_url,))
        
        #obtain the book id:
        book_id = cur.execute("SELECT id FROM books WHERE google_id=?",  (id,)).fetchall()[0]['id']
        #now link the book to its authors in the relevant tables:
        #if the book has valid author ids insert  the links into the book_authors table
        if not ((len(author_ids) == 1) and (author_ids[0] == 0)):
            unique_authors = set(author_ids)
            for author_id in unique_authors:
                cur.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?,?)", (book_id, author_id,))

    cur.execute("COMMIT")
    con.close()
    return book_id


# turns a google search response into canonical list of book-dictionaries
def google_results_to_list(results):
    book_list = []
    for i in range(len(results["items"])):
        book = results["items"][i]
        book_dict = {}
        try:
            book_dict["title"] = book["volumeInfo"]["title"]
        except:
            book_dict["title"] = ""
        try:
            subtitle = book["volumeInfo"]["subtitle"]
            if subtitle == "A Novel":
                book_dict["subtitle"] = ""
            else:
                book_dict["subtitle"] = subtitle
        except:
            book_dict["subtitle"] = ""
        try:
            authors = book["volumeInfo"]["authors"]
            #assemble a list of tuples where each tuple is a lastname, firstname pair corresponding to one author
            authorTuples = []
            n = len(authors)
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
            book_dict["authors"] = author_str
        except:
            book_dict["authors"] = ""
        try:
            book_dict["year"] = book["volumeInfo"]["publishedDate"][0:4]
        except:
            book_dict["year"] = ""
        try:
            book_dict["ebook"] = book["saleInfo"]["isEbook"]
        except:
            book_dict["ebook"] = "Unknown"
        try:
            cover_url = book["volumeInfo"]["imageLinks"]["smallThumbnail"]
            if "&edge=curl" in cover_url:
                cover_url = cover_url.replace("&edge=curl", "")
            if "edge=curl&" in cover_url:
                cover_url = cover_url.replace("edge=curl&", "")
            book_dict["cover"] = cover_url
        except:
            book_dict["cover"] = ""
        book_dict["id"] = book["id"]
        book_dict["suffix"] = ""
        book_list.append(book_dict)
    return book_list

# single book results from isbnlib to canonical dictionary format
def isbn_results_to_list(results, isbn, suffix):
    book_list = []
    book_dict = {}
    try:
        book_dict["title"] = results["Title"]
    except:
        book_dict["title"] = ""
    book_dict["subtitle"] = ""
    try:
        authors = results["Authors"]
        #assemble a list of tuples where each tuple is a lastname, firstname pair corresponding to one author
        authorTuples = []
        n = len(authors)
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
        book_dict["authors"] = author_str
    except:
        book_dict["authors"] = ""
    try:
        book_dict["year"] = results["Year"]
    except:
        book_dict["year"] = ""
    book_dict["ebook"] = "Unknown"
    try:
        image_results = cover(isbn)
        cover_url = image_results["smallThumbnail"]
    except:
        try:
            image_results = cover(isbn)
            cover_url = image_results["thumbnail"]
        except:
            cover_url = ""
    book_dict["cover"] = cover_url
    book_dict["id"] = "ISBN" + isbn
    book_dict["suffix"] = suffix
    book_list.append(book_dict)
    return book_list


# define decorator that redirects anyone not logged in to the login page
# from https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# checks a list of books for presence in users library/wishlist and appends this infomation to the books
def stock_check(book_results):
    #get the user's id
    user_id = session["user_id"]

    # iterate through the books and check for their presence in the user's DB
    con = sqlite3.connect('booktree.db')
    con.row_factory = dict_factory
    cur=con.cursor()
    for book in book_results:
        #first determine whether the book is even in the main library and get its id
        book_id = book["id"]
        #if it si an ISBN result, remove the suffix
        if book_id[0:4] == 'ISBN':
            if book_id[-5:] == 'openl':
                book_id = book_id[:-5]
            elif book_id[-4:] == 'wiki':
                book_id = book_id[:-4]
        # determine if there are any books owned by the user with this ID:
        sqlcommand = "SELECT id FROM books WHERE id in (SELECT book_id FROM library WHERE user_id=?) AND google_id=?"
        rows = cur.execute(sqlcommand, (user_id, book_id,)).fetchall()
        #  add whether the book is in the library to the dictionary
        if(len(rows) == 1):
            book["inlib"] = True
        else:
            book["inlib"] = False
        
        #check whether the user's wishlist contains any books with this id
        sqlcommand = "SELECT id FROM books WHERE id in (SELECT book_id FROM wishlist WHERE user_id=?) AND google_id=?"
        rows = cur.execute(sqlcommand, (user_id, book_id,)).fetchall()
        #  add whether the book is in the wishlist to the dictionary
        if(len(rows) == 1):
            book["inwish"] = True
        else:
            book["inwish"] = False
    con.close()
    return book_results
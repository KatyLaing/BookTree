# BookTree

#### [Find a video demo of BookTree here](https://youtu.be/6JjB6mI4LRY).

## General
BookTree is a web application built using the python Flask framework with a SQLite database. The app is a book database which allows you to catalogue and organise your existing library of books (and eBooks) and create book wishlists. As a personal hoarder of books this app was built to answer the question I ask in every bookshop I wander into - "Have I got this book already?". However, the capabilities of this app also enable the user to store book reviews, keep track of borrowed/lent copies, track their reading progress, organise their books and more.

  * [App Features & Design Choices](#app-features--design-choices)
    * [Registration, Logging In, and Logging out](#registration-logging-in-and-logging-out)
    * [Book Search](#book-search)
    * [Search Results](#search-results)
    * [Book Summary Pages](#book-summary-pages)
    * [Default Bookshelves](#default-bookshelves)
    * [Custom Bookshelves](#custom-bookshelves)
    * [Wishlist](#wishlist)
    * [Backend Details](#backend-details)
  * [SQL Database](#sql-database)
    * [Schema](#schema)
    * [Transactions](#transactions)
  * [Source Code](#source-code)
  * [The Future](#the-future)

## App Features & Design Choices
### Registration, Logging In, and Logging out
Registration requires a name, a valid email address (at least in the sense of email format), and matching passwords of 8-20 characters in length (these password fields have  a toggle to view option). These requirements are enforced by javascript in the fields before submission and checked again by python on the server side. Passwords are encrypted via SHA-256 Crypt password hash. Users log in using their email and password and user identification is then stored in the user session. This is cleared on log out.  The navigation bar options change on successful log in from Register and Log In to displaying all book shelves, search, and Log Out option. Due to a `login_required` decorator on most routes, if users that are not logged in (i.e. have no user ID in their session) try to access any part of the site other than home, register, or log in, they will be automatically redirected to the log in page.

### Book Search
Users can find books to add to their library or wishlists via the Book Search tab. This allows the user to search for a book via title, author, or ISBN (ISBN-10 or ISBN-13). Title or author searches are done via querying the Google Books API. ISBN searches use the [isbnlib](https://github.com/xlcnd/isbnlib) python library and use both the wiki and open library APIs (first searching the wiki database and then the open library if there are no results). If the ISBN search does not produce results and no other search term is specified, then we search Google Books for the ISBN (as this occasionally will find another version of the same book). These searches are performed via AJAX post requests so that searches do not refresh the page and remain private.

Google Books API is generally very good at finding the correct book and displaying relevant additional results. I chose to include the ISBN search tool as well as Google Books as it enables you to search for the specific version of a book that you own. This is particularly important if you want the correct edition of a book (in particular, with the correct cover art). In general, I found that some UK or older editions would not come up in the Google Books search results. However in practice, I have found that almost all books can be found in the desired edition via one of these two methods of search.

### Search Results
Search results display the cover art, title, author, year, and format (book, ebook, or unknown) of the book and you can click on the title to go to the book summary page (described below) for more information. If cover art is not supplied by the API, a stock image with "Cover unavailable" is displayed. Search results also have "Add to/Remove from library" and "Add to/Remove from wishlist" buttons next to them meaning you can add/remove titles directly from the search results page. These buttons are responsive and change between "Add to" and "Remove from" as appropriate on click. As an extra feature, if a book in your wishlist is added to your library it will automatically be taken out of your wishlist. Adding and removing happens via AJAX post requests so that the page does not refresh, meaning multiple titles can be added or removed at once. If a book is removed from your library it is also removed from all custom shelves as well.

Here, and in general accross the app, page buttons are disabled for the duration of a JS function/AJAX request. This gives the user some feedback about the status of their request if it does not happen instantly, as well as discouraging double clicks or spamming requests if server response times should be slow.

### Book Summary Pages
Every book has a summary page which goes into more detail about the book. This page will appear differently depending on whether the book is in your library or not. Summary pages can be accessed by clicking on a book's title from anywhere - search results, library, bookshelves, or your wishlist.

These summary pages include the title, author, year, format, publisher, ISBN-10/13, number of pages, genre(s), cover art, and a summary of the book (if known from the Google Books/isbnlib API). This page also includes a link to view and/or buy the book from Google Books where possible as well as buttons to add/remove the book from the user's library and/or wishlist. On these pages, adding or removing a book from your library *will* refresh the page as this impacts how the summary page should appear.

If the user has the book in their library, user data is also displayed and can be modified from this page. Firstly, if the number of pages is known, there is an (javascript) animated circular progress bar displaying the percentage of the book the user has read. Progress is a rounded percentage except in the case of 0% and 100% - these will only display if none or all pages have been read as I feel this gives a better user experience. The user can increment or input pages read and the progress will smoothly update.  Once all pages have been read, the number of times the user has read the book automatically increments and the progress bar displays a "Read Again" button which will re-set progress to 0%. If the user inputs a page number the animation should be a smooth transition, if the user increments the page number up/down then the progress jumps instantly. The latter is in order for the animation to keep up with the speed of user clicks. Non-integer values of pages are not permitted by the JS update function for the progress bar, or by the server when updating the database.

The number of times the user has read a book is also displayed and can be directly incremented via +/- buttons (adding a read to the book in this way automatically changes progress to 100%). Any time a user completes a book - either by reaching 100% progress or incrementing this counter - a pop up alert will appear congratulating the user on completing another book. All pop up alerts and forms are implemented via the [Sweet Alerts](https://sweetalert.js.org/) javascript package.

There is also an animated 5 star rating scale, displaying the user's rating of the book. This can be changed simply by clicking on the desired star. Finally, there is a notes section displaying notes that the user has made on the book. They can edit this here by writing in the text box and clicking save to update the notes on the database. 

All of the user data is editable directly from this page and is updated in the database via AJAX requests for a smoother experience.

### Default Bookshelves
Every user's library is initiated with four default shelves - All Books, In Progress, Read, and Unread. All Books shows all books in the user's library. In progress shows all books that currently have a non-zero number of pages read (in the case of books with unknown pages, they are considered in progress until the user has read them at least once). Read shows all books with a positive number of reads and Unread displays those with zero.

Clicking into any of these shelves will display a list of books similar to the search results with the addition of the user's star rating. As all books on these shelves are in the user's library, the only displayed button here is "Remove from Library". If the user has any custom bookshelves (described below), a drop down form will be displayed, allowing users to add books to these bookshelves. Books are added via selecting their checkbox (or using the select all option) and selecting a custom shelf from the drop down list. This action takes you to the specified shelf to see the result.

If default shelves have more than one book then a sorting and searching form is displayed. This allows you to sort books by title, author, date added to your library, date modified (by updating book data such as notes or pages read), or by user rating. There is also an option to search the bookshelf by words in the title (searching for exact substrings) or author names (searching for any author list that contains one search term as a substring to allow the user to write authors in any order). Searching the shelf resets the sorting back to default. If you search the list, then these results can also be sorted. Sorting and searching is done via AJAX requests for a smoother interaction for the user.

### Custom Bookshelves
Users can add a custom bookshelf from any page via the "Add a New Shelf" option in the navigation bar. This displays a pop up asking for a shelf title, creates the new shelf, then displays a pop up confirmation and reloads the page. If the page was loaded via post request, this reload is done by re-submitting the information to the server (avoiding the alert asking the user to confirm re-submission). If the user already has a shelf with the specified title an error warning pop up will display instead. Users' custom shelves are stored in their session so that they can be displayed (and accessible) via the navigation bar. Going into a custom shelf, users see the same information and sort/search options as the default shelves. The only difference is that books cannot be added to other custom bookshelves from these pages and a "Remove from Shelf" button replaces "Remove from Library".

These custom bookshelves can be edited via the "Edit shelves" option in the navigation bar. This takes you to a page where you can select any shelf and be presented (via pop-up) with the option to either rename or delete the shelf.

### Wishlist
The user automatically gets a wishlist shelf where they can view any books they have added to their  wishlist. These books are displayed in the same way as the search results - no user ratings, or ability to add to custom bookshelves is available here as these are only options for library books. Books are presented with the options of "Remove from Wishlist" and "Add to Library". This list is sortable and searchable when there is more than one book present with the exception of sorting by rating or date modified as these are not applicable for wishlist books.

### Backend Details
All HTTP requests involving user data or identifiable book data are made using post requests for user privacy.

All python functions on the server are coded defensively to ensure users can't cause problems by modifying the passed arguments. All request data has its format verified on the server, I use placeholders to protect against SQL injection attacks, and check for every request that the user "owns" the books or shelves that they are trying to modify. Any invalid requests sent to the server return error messages or empty results so that the user does not see "Internal Service Error" or the like.

## SQL Database

### Schema
I used a SQLite3 relational database to store the user and book data. The schema of the database is given below and there is more detail (in particular about constraints and default values) available on the [interactive schema diagram](https://dbdiagram.io/embed/610921ba2ecb310fc3bb59ee).

User login details are stored in `users`. Global book data is stored in `books`, this is initially empty and we add to it as users add books to their libraries and wishlists. The `google_id` is the Google Books unique ID for this book except when the book is found via ISBN search, in which case this is the books ISBN code. `books` is linked to several other tables of book properties in order to reduce redundancies in the database. The `format` table encodes the 3 possible format options (Book, Ebook, Unknown) with 3 format IDs (1,2,3) and is never altered. Languages are given in 2 letter ISO codes, hence the `char(2)` data type. `library` and `wishlist` store which books each user has in their library/wishlist. `library` also stores user-specific book data such as notes, ratings, number of reads etc. `in-progress` is a variable that takes value 1 if the book is currently at 100% complete and value 0 otherwise - this affects how the book summary page displays. `user_shelves` shows us which shelves belong to which users and `book_shelves` specifies what books are on each shelf.

![BookTreeDB](https://user-images.githubusercontent.com/80559169/128012432-e7c8a1d3-e5e8-4dea-bfeb-73e8b2917124.png)

### Transactions
Explicit BEGIN/COMMIT transactions have been used in my SQLite commands in order to group interactions with the database where we are modifying our data. This will allow for multiple users to interact with the app safely as race conditions are avoided.

## Source Code
Below I give an overview of the source code directory:

  * `application.py` Is where the main application is located.
  * `additionalFunctions.py` Contains several helper functions for the main route functions.
  * `.env` Contains flask configuration variables. Requires a valid Google Books API key in order for the application to run
  * `templates` Contains the HTML/Jinja files
    * `bookinfo.html` HTML template for book summary pages
    * `bookshelf.html` HTML template for displaying a custom bookshelf
    * `index.html` Homepage HTML
    * `layout.html` HTML template extended by all other HTML files, this gives the top navigation bar and the ability to display flashed messages on every page
    * `login.html` Log in page HTML
    * `nobook.html` HTML page to display if the user attempts to view a book summary without specifying a valid book
    * `register.html` Registration form HTML
    * `search.html` HTML template for searching books and displaying the results
    * `shelvesEdit.html` Custom shelf editing page HTML
    * `wishlist.html` HTML template for displaying the user's wishlist
  * `static` Contains all CSS, Javascript, icon, and image files
    * `booksummary.css` CSS for book summary page but more generally used for the formatting of bootstrap cards (card formatting from [bootdey.com](https://www.bootdey.com))
    * `dropdown.css` CSS for the navigation bar dropdown menu and submenu (modified from [mdbootstrap.com](https://mdbootstrap.com))
    * `progressbar.css` CSS for the animated progress bar on book summary page (from [bootstrapious.com](https://bootstrapious.com))
    * `spinner.css` CSS for the loading spinner (from [loading.io](https://loading.io/))
    * `stars.css` CSS for the animated 5 star rating (from [bbbootstrap.com](https://bbbootstrap.com))
    * `styles.css` General CSS applied to all pages
    * `addRemoveBooks.js` JS functions to make the add to/remove from library/wishlist buttons work
    * `booksearch.js` JS function for submitting book searches and displaying the results
    * `progressbar.js` JS functions to make the page progress bar on book summary pages animate and interact with other page features correctly
    * `readIncrement.js` JS function that enable the +/- buttons to correctly increment the number of reads and interact with other page features
    * `shelves.js` JS script adding an event listener that makes the "Add custom shelf" feature work
    * `SortSearchDisplay.js` JS functions that enable the sorting and search of default shelves, custom shelves, and the wishlist


## The Future
Currently BookTree has only been run for demo purposes using a local computer as the server. The next step will be to set it up on a real server for 24/7 access.

Other features I would like to add to this application in future:
  * A statistics page, showing how your library has grown over time, your read-unread ratios, total number of pages read over time etc.
  * Make BookTree work on mobile formats
  * The ability to scan barcodes to obtain the ISBN when accessing the site on a phone.
  * Allowing more customisation of the books in your library - perhaps being able to upload your own covers (particularly when none is available from the API) or even add entirely custom books if you can't find the exact book/version you're looking for.
  * Expand the formats to audiobooks as well, which will require a new data source
  * Add some rating of "urgency" to the books in wishlist

TrelloPrinter
=============

Trello board printer: generate a printable version of a Trello board including card descriptions and attachments.

Usage: Open a Trello board, go to the menu of the board and click the "Share, Print and Export" option. Click the "Export to JSON" option and download the resulting json file. Call this program using the downloaded file as input. For example:

    python trello_printer.py <trello_board.json -o MyBoard

trello_printer.py will then:
 1. Create a printable version of the board, including card descriptions.
 2. Download all the (non-archived) card attachments which are stored in Amazon.
 3. Bundle the printable version of the board with the downloaded attachments into MyBoard.pdf.

You can change the board print template by editing trello_printer.py. You can goto https://github.com/nicolasbrailo/TrelloPrinter and request a user-friendlier template edition. Actually, you can go over there and request any feature you'd like.

Dependencies:
=============
Python, wkhtmltopdf, ghostscript + pystache and pdfkit
In Ubuntu:

    sudo apt-get install wkhtmltopdf ghostscript python python-pip 
    pip install pystache pdfkit



# Template used to print a Trello board. Uses pystache.
board_template = """
<html>
<head>
<meta content="text/html;charset=utf-8" http-equiv="Content-Type">
<meta content="utf-8" http-equiv="encoding">
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap.min.css">
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap-theme.min.css">
<style>
.card {
  margin: 5px;
  border:1px solid black;
  width: 48%;
  display: inline-block;
  vertical-align: top;
} .longcard {
  margin: 5px;
  border:1px solid black;
  width: 98%;
} .list {
  clear: both;
  margin-top: 10px;
  padding-top: 10px;
  border-top:3px dotted black;
}

@media print
{   
    .no-print, .no-print *
    {
        display: none !important;
    }

    div{
        page-break-inside: avoid;
    }

    a[href]:after {
      content: none !important;
    }
}
</style>
</head>

<body>
<h2>Board {{{name}}}</h2>
by {{#members}}{{{fullName}}}, {{/members}}Last activity: {{dateLastActivity}} /
<a href='{{url}}'>{{url}}</a>

{{#activeLists}}
  <div class="list">
  <h3>{{{name}}}</h3>

  {{#activeCards}}
    <div class="col-md-6 card">
      <h4><a href='{{url}}'>{{{name}}}</a></h4>
      <p>
      {{{desc}}}
      </p>

      {{#checklists}}
        <ul>
        {{#checkItems}}
          <li>{{{name}}}</li>
        {{/checkItems}}
        </ul>
      {{/checklists}}
 
      <div class="no-print">
        {{#attachments}} | <a href="{{url}}">{{name}}</a>{{/attachments}}
      </div>
    </div>
  {{/activeCards}}

  {{#activeLongCards}}
    <div class="col-md-6 longcard">
      <h4><a href='{{url}}'>{{{name}}}</a></h4>
      <p>
      {{{desc}}}
      </p>

      {{#checklists}}
        <ul>
        {{#checkItems}}
          <li>{{{name}}}</li>
        {{/checkItems}}
        </ul>
      {{/checklists}}
 
      <div class="no-print">
        {{#attachments}} | <a href="{{url}}">{{name}}</a>{{/attachments}}
      </div>
    </div>
  {{/activeLongCards}}
  </div>

{{/activeLists}}
</body>

<html>
"""


import pystache
import cgi
import codecs

class Trello_Board(object):
  def __init__(self, json_object, big_card_min_words):
    self.board_json = self._transmogrify_trello_board(json_object, big_card_min_words)

  def html_render(self, template):
    return pystache.render(template, self.board_json).encode('utf-8')

  def get_pdf_attachments(self):
    attachments = []
    for lst in self.board_json['activeLists']:
      for card in lst['activeCards']:
        for attach in card['attachments']:
          if attach['url'].endswith(".pdf"):
            attachments.append(attach['url'])

    return attachments

  def _formatDates(self, obj, fields):
    for field in fields:
      obj[field] = obj[field][:obj[field].find('T')]
    return obj

  def _prettyHtml(self, obj, fields):
    for field in fields:
      htmlified = cgi.escape(obj[field]).encode('ascii', 'xmlcharrefreplace')
      htmlified = htmlified.replace('\n', '<br/>')
      obj[field] = htmlified
    return obj

  def _transmogrify_trello_board(self, board, big_card_min_words):
    """ Transform a plain Trello format (list of stuff) to a hierarchical model
    more suitable for pystache """
    board = self._prettyHtml(board, ['name'])
    board = self._formatDates(board, ['dateLastActivity'])

    # Htmlize the members names
    for o in board['members']:
      o = self._prettyHtml(o, ['fullName'])

    # Create list of active trello-lists
    board['activeLists'] = []
    for lst in board['lists']:
      if lst['closed']: continue

      # Get all the non-closed cards for this list
      activeCards = [ self._formatDates(self._prettyHtml(card, ['name', 'desc']), ['dateLastActivity']) \
                             for card in board['cards'] \
                             if card['idList'] == lst['id'] \
                                and not card['closed'] ]

      lst['activeCards'] = [card for card in activeCards if len(card['desc']) < big_card_min_words]
      lst['activeLongCards'] = [card for card in activeCards if len(card['desc']) >= big_card_min_words]

      # Get all the active checklists
      for card in lst['activeCards']:
        card['checklists'] = [checklist for checklist in board['checklists']
                                if checklist["idCard"]==card["id"] ]
        for cl in card['checklists']:
          for item in cl['checkItems']:
            item = self._prettyHtml(item, ['name'])

      lst = self._prettyHtml(lst, ['name'])
      board['activeLists'].append(lst)

    return board



import json
import cgi
import codecs
import sys
import tempfile
import pdfkit
import os
import urllib2


def pretty_print(jstuff):
  return json.dumps(jstuff, sort_keys=True, indent=4, separators=(',', ': '))


def read_json_board(fp, big_card_min_words):
  trello_json = ""
  for ln in codecs.getreader('utf-8')(fp).readlines():
    trello_json += ln

  return Trello_Board(json.loads(trello_json), big_card_min_words)

def create_pdf_bundle(args, board):
  # List of all pdf files to join
  pdfs_to_join = []

  # Print temp pdf board from html, to be used by pdf joiner
  tmp_board_pdf = tempfile.NamedTemporaryFile(delete=False)
  if not args.quiet: print >> sys.stderr, "Generating temporary board pdf in {}...".format(tmp_board_pdf.name)
  pdfkit.from_string(board.html_render(board_template), tmp_board_pdf.name)
  pdfs_to_join.append(tmp_board_pdf)

  # Fetch the board's attachments
  if args.bundle_attachments:
    for url in board.get_pdf_attachments():
      f = tempfile.NamedTemporaryFile(delete=False)
      if not args.quiet: print >> sys.stderr, "Downloading attachment {} into {}...".format(url, f.name)
      f.write( urllib2.urlopen(url).read() )
      pdfs_to_join.append(f)

  # exec
  out_fname = args.out_fname
  if out_fname is None:
    out_fname = sys.argv[0] + '_bundle.pdf'
  else:
    out_fname += '.pdf'

  # Save the fnames and close them, if we hold these files open ghostscript goes haywire
  join_fnames = ' '.join([f.name for f in pdfs_to_join])
  for f in pdfs_to_join:
    f.close()

  if not args.quiet: print >> sys.stderr, "Generating bundle {}:".format(out_fname)
  pdf_join_cmd = 'gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile={} {}'\
                    .format(out_fname, join_fnames)
  if not args.quiet: print >> sys.stderr, "Running {}".format(pdf_join_cmd)
  os.system(pdf_join_cmd)

  # Clean up temp files
  for fn in pdfs_to_join: os.remove(fn.name)


def main(args):
  board = read_json_board(sys.stdin, args.big_card_min_words)
  if not args.quiet: print >> sys.stderr, "Valid board found!"

  if args.html_output:
    f = sys.stdout
    if args.out_fname is not None:
      f = open(args.out_fname + '.html', 'w+')
    print >> f, board.html_render(board_template)

  if args.print_debug_json:
    f = sys.stdout
    if args.out_fname is not None:
      f = open(args.out_fname + '.json', 'w+')
    print >> f, pretty_print(board.board_json)

  if args.create_pdf_bundle:
    create_pdf_bundle(args, board)


import argparse
import sys

app_desc = """
Trello board printer: generate a printable version of a Trello board including card descriptions and attachments.

Usage: Open a Trello board, go to the menu of the board and click the "Share, Print and Export" \
option. Click the "Export to JSON" option and download the resulting json file. Call this program \
using the downloaded file as input. For example:

    python {0} <trello_board.json -o MyBoard

{0} will then:
 1. Create a printable version of the board, including card descriptions.
 2. Download all the (non-archived) card attachments which are stored in Amazon.
 3. Bundle the printable version of the board with the downloaded attachments into MyBoard.pdf.

You can change the board print template by editing {0}. You can goto \
https://github.com/nicolasbrailo/TrelloPrinter and request a user-friendlier template edition. \
Actually, you can go over there and request any feature you'd like.

"""
parser = argparse.ArgumentParser(description=app_desc.format(sys.argv[0]),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("-o", "--output", dest="out_fname",
                    default=None, metavar="FILE_NAME",
                    help="Use FILE_NAME for output (eg: Specify '-o MyBoard --html \
                          --debug' to generate MyBoard.json and MyBoard.html).")
parser.add_argument("--no-attachments", action="store_false",
                    dest="bundle_attachments", default=True,
                    help="Don't download and bundle pdf attachments in final printable document.")
parser.add_argument("--html", action="store_true",
                    dest="html_output", default=False,
                    help="Output only an HTML version of the board.")
parser.add_argument("--no-bundle", action="store_false",
                    dest="create_pdf_bundle", default=True,
                    help="Don't create a pdf bundle of the specified board.")
parser.add_argument("--debug", action="store_true",
                    dest="print_debug_json", default=False,
                    help="Output a prettyfied version of the board's json.")
parser.add_argument("-m", "--min_words", type=int, metavar='N',
                    dest="big_card_min_words", default=800,
                    help="Number of words after which a card is considered 'big'. "\
                         "A single column layout is used for big cards. [800]")
parser.add_argument("-q", "--quiet", action="store_true",
                    dest="quiet", default=False,
                    help="Run in quiet mode.")

if __name__ == '__main__':
  main(parser.parse_args())


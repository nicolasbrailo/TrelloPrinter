import pystache
#sudo apt-get install wkhtmltopdf
import pdfkit
import urllib2
import json
import sys
import cgi
import codecs
import time

template = """
<html>
<head>
<meta content="text/html;charset=
utf-8" http-equiv="Content-Type">
<meta content="utf-8" http-equiv="encoding">
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap.min.css">
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap-theme.min.css">
<style>
body
{
  font-size: 10px;
} .card {
  margin: 5px;
  border:1px solid black;
  width: 48%;
  display: inline-block;
  vertical-align: top;
} .list {
  width: 99%;
}
</style>
</head>

<body>
<h2>Board {{{name}}}</h2>
by {{#members}}{{{fullName}}}, {{/members}}Last activity: {{dateLastActivity}} /
<a href='{{url}}'>{{url}}</a>

{{#activeLists}}
  <hr class="row"/>
  <div class="list">
  <h3>{{{name}}}</h3>

  {{#activeCards}}
    <div class="col-md-6 card">
      <h4><a href='{{url}}'>{{{name}}}</a></h4>
      <p>
      {{{desc}}}
      </p>

      Updated: {{dateLastActivity}}
      {{#attachments}} | <a href="{{url}}">{{name}}</a>{{/attachments}}

      <!--
      {#attachments}
        <embed type='application/pdf' src="{url}" width="100%" height="100%">
      {/attachments}
      -->

    </div>
  {{/activeCards}}
  </div>

{{/activeLists}}
</body>

<html>
"""

def pretty_print(jstuff):
  print json.dumps(jstuff, sort_keys=True, indent=4, separators=(',', ': '))

class Trello_Board(object):
  def __init__(self, json_object):
    self.board = self._transmogrify_trello_board(json_object)

  def html_render(self):
    return pystache.render(template, board.board).encode('utf-8')

  def get_pdf_attachments(self):
    attachments = []
    for lst in self.board['activeLists']:
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

  def _transmogrify_trello_board(self, board):
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
      lst['activeCards'] = [ self._formatDates(self._prettyHtml(card, ['name', 'desc']), ['dateLastActivity']) \
                             for card in board['cards'] \
                             if card['idList'] == lst['id'] \
                                and not card['closed'] ]

      lst = self._prettyHtml(lst, ['name'])
      board['activeLists'].append(lst)

    return board



trello_json = ""
for ln in codecs.getreader('utf-8')(sys.stdin).readlines():
  trello_json += ln

board = Trello_Board(json.loads(trello_json))
#pretty_print(board.board)
#print board.html_render()

def get_fname(url):
  return url[url.rfind('/')+1:]

pdfkit.from_string(board.html_render(), 'trello_board.pdf')
downloaded = []
for url in board.get_pdf_attachments():
  fname = get_fname(url)
  open(fname, "w+").write( urllib2.urlopen(url).read() )
  downloaded.append(fname)

to_join = 'trello_board.pdf ' + ' '.join(downloaded)
pdf_join = 'gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile=out.pdf ' + to_join

import os
os.system(pdf_join)



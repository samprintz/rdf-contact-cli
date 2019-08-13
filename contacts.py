from rdflib import Graph
from rdflib import URIRef
from rdflib import BNode
from rdflib import Literal
from rdflib.namespace import RDF

import urwid
import curses

import operator

PATH = 'test.n3'
GIVEN_NAME_REF = URIRef('http://hiea.de/contact#givenName')
g = None


### N3 functions

def loadFile(path):
    g = Graph()
    g.parse(path, format="n3")
    return g

def saveFile(path):
    g.serialize(format='n3', indent=True, destination=path)


def getContacts():
    contacts = []
    for s,p,o in g.triples( (None, GIVEN_NAME_REF, None) ):
        contacts.append(str(o))
        contacts.sort()
    return contacts

def containsContact(name):
    return (None, GIVEN_NAME_REF, Literal(name)) in g

def addContact(name):
    if containsContact(name):
        return [name, " already exists."]
    else:
        g.add( (BNode(), GIVEN_NAME_REF, Literal(name)) )
        saveFile(PATH)
        return [name, " added."]

def removeContact(name):
    if containsContact(name):
        g.remove( (None, GIVEN_NAME_REF, Literal(name)) )
        saveFile(PATH)
        return [name, " removed."]
    else:
        return [name, " doesn't exists."]


### urwid

class MenuButton(urwid.Button):
    def __init__(self, caption, callback):
        super(MenuButton, self).__init__("")
        urwid.connect_signal(self, 'click', callback)
        self._w = urwid.AttrMap(urwid.SelectableIcon(
            caption, 100), None, 'selected')
            #[u'  \N{BULLET} ', caption], 2), None, 'selected')

    def keypress(self, size, key):
        if key == 'a':
            add()
        elif key == 'h':
            name = str(self._w._original_widget.text)
            remove(name)
        elif key == 'e':
            #TODO
            name = self._w._original_widget.text
            edit = urwid.Edit(caption=u":TODO: edit ", edit_text=name)
            fill.footer = urwid.BoxAdapter(Command(edit), height=1)
            return super(MenuButton, self).keypress(size, key)
        else:
            return super(MenuButton, self).keypress(size, key)

class SubMenu(urwid.WidgetWrap):
    def __init__(self, caption, choices):
        super(SubMenu, self).__init__(MenuButton(caption, self.open_menu))
        line = urwid.Divider(u'\N{LOWER ONE QUARTER BLOCK}')
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker([
            urwid.AttrMap(urwid.Text([u"\n", caption]), 'heading'),
            urwid.AttrMap(line, 'line'),
            urwid.Divider()] + choices + [urwid.Divider()]))
        self.menu = urwid.AttrMap(listbox, 'options')
        self.caption = caption

    def open_menu(self, button):
        top.open_box(self.menu)

    def keypress(self, size, key):
        if key == 't':
            #TODO
            #self.menu._original_widget.change_focus(size, 5)
            #position = self.menu._original_widget._body.next_position
            #self.menu._original_widget._body.set_focus(position)
            #name = str(self.menu._original_widget._body.next_position)
            #name = str(self.menu._original_widget.get_focus())
            #edit = urwid.Edit(caption=u":", edit_text=name)
            #fill.footer = urwid.BoxAdapter(Command(edit), height=5)
            return super(SubMenu, self).keypress(size, key)
        if key == 'r':
            return super(SubMenu, self).keypress(size, key)
        else:
            return super(SubMenu, self).keypress(size, key)


class Choice(urwid.WidgetWrap):
    def __init__(self, caption):
        super(Choice, self).__init__(
            MenuButton(caption, self.item_chosen))
        self.caption = caption

    def item_chosen(self, button):
        response = urwid.Text([u'  You chose ', self.caption, u'\n'])
        done = MenuButton(u'Ok', exit_program)
        response_box = urwid.Filler(urwid.Pile([response, done]))
        top.open_box(urwid.AttrMap(response_box, 'options'))

def exit_program(key):
    raise urwid.ExitMainLoop()


palette = [
    (None,  'light gray', 'black'),
    ('heading', 'light gray', 'black'),
    ('line', 'black', 'black'),
    ('options', 'light gray', 'black'),
    ('focus heading', 'light gray', 'black'),
    ('focus line', 'black', 'black'),
    ('focus options', 'light gray', 'black'),
    ('selected', 'black', 'light gray')]
focus_map = {
    'heading': 'focus heading',
    'options': 'focus options',
    'line': 'focus line'}

class HorizontalBoxes(urwid.Columns):
    def __init__(self):
        super(HorizontalBoxes, self).__init__([], dividechars=1)

    def open_box(self, box):
        if self.contents:
            del self.contents[self.focus_position + 1:]
        self.contents.append((urwid.AttrMap(box, 'options', focus_map),
            self.options('given', 24)))
        self.focus_position = len(self.contents) - 1

def navigation(key):
    if key in keyCommands.keys():
        keyCommands[key]()

def exit():
    raise urwid.ExitMainLoop()

class Command(urwid.Filler):
    def keypress(self, size, key):
        if key == 'esc':
            fill.footer = None
            fill.set_focus('body')
        if key != 'enter':
            return super(Command, self).keypress(size, key)
        args = self.original_widget.edit_text.split()
        command = args[0]
        if command in ('add'):
            name = args[1]
            msg = addContact(name)
            updateMenu()
        elif command in ('remove', 'del', 'rm'):
            name = args[1]
            msg = removeContact(name)
            updateMenu()
        else:
            msg = 'Not a valid command.'
        self.original_widget = urwid.Text(msg)
        fill.set_focus('body')

def add():
    edit = urwid.Edit(caption=u":", edit_text=u"add ")
    fill.footer = urwid.BoxAdapter(Command(edit), height=1)
    fill.set_focus('footer')

def remove(name):
    edit = urwid.Edit(caption=u":", edit_text="remove {}".format(name))
    fill.footer = urwid.BoxAdapter(Command(edit), height=1)
    fill.set_focus('footer')

def edit(name):
    return

keyCommands = {
        'q' : exit,
        'Q' : exit}


def loadMenu():
    global g
    g = loadFile(PATH)
    contact_menu = []
    for s,p,o in g.triples( (None, GIVEN_NAME_REF, None) ):
        # attributes
        # TODO make unique (giftIdea only once)
        attributes = []
        for s2,p2,o2 in g.triples( (s, None, None) ):
            # values
            values = []
            for s3,p3,o3 in g.triples( (s, p2, None) ):
                value = Choice(str(o3))
                values.append(value)
            values.sort(key=operator.attrgetter('caption'))
            attribute_menu = SubMenu(str(p2.split("#",1)[1]), values)
            attributes.append(attribute_menu)
        attributes.sort(key=operator.attrgetter('caption'))
        menu_entry = SubMenu(str(o), attributes)
        contact_menu.append(menu_entry)
    contact_menu.sort(key=operator.attrgetter('caption'))
    menu_top = SubMenu(u'Contacts', contact_menu)
    return menu_top

def updateMenu():
    menu_top = loadMenu()
    top = HorizontalBoxes()
    top.open_box(menu_top.menu)
    fill.body = top
    fill.set_focus('body')
    


menu_top = loadMenu()
top = HorizontalBoxes()
top.open_box(menu_top.menu)
#fill = urwid.Filler(top, valign='top', height=('relative', 100))
fill = urwid.Frame(top)
loop = urwid.MainLoop(fill, palette, unhandled_input=navigation)
loop.run()

from datetime import date,datetime
import urwid
import pudb

from objects import *
import cli


class ContactLoop(urwid.MainLoop):
    def __init__(self, frame, config):
        palette = config['display']['palette']
        loop = urwid.MainLoop(frame, palette, unhandled_input=self.show_or_exit)
        loop.run()

    def show_or_exit(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()


class ContactFrame(urwid.Frame):
    def __init__(self, config, core):
        super(ContactFrame, self).__init__(None)
        self.config = config
        self.core = core
        self.set_footer()

    def set_contact_list(self, contact_list):
        focus_map = self.config['display']['focus_map']
        self.body = ContactFrameColumns(contact_list, self.core, self.config)
        self.contact_list = self.body.contents[0][0].base_widget
        self.set_contact_details()

    def set_contact_details(self):
        contact = self.contact_list.get_focused_contact()
        contact.get_details() # augment existing contact with details (not before for performance)
        if len(self.body.contents) > 1:
            del self.body.contents[1]
        self.body.set_contact_details(contact)
        self.contact_details = self.body.contents[1][0].base_widget

    def refresh_contact_list(self, focused_contact=None, position=None):
        last_focused_contact = self.contact_list.get_focused_contact()

        contact_list = self.core.get_all_contacts()
        self.set_contact_list(contact_list)

        # contact added or renamed: focus (new) contact / same contact
        if focused_contact is not None: # 
            pos = self.contact_list.get_contact_position(focused_contact)
        else:
            # contact deleted: focus previous contact
            if position is not None:
                if position == 0: # if first contact: jump to first
                    pos = 0
                else: # generally: focus previous
                    pos = position - 1
            # list refresh (ctrl+r): focus contact that was focused before refresh
            else:
                pos = self.contact_list.get_contact_position(last_focused_contact)
                if pos is None: # if in tests no contact was focused before
                    pos = 0

        self.contact_list.set_focus_position(pos)

    def set_header(self):
        pass

    def set_footer(self):
        self.footer = urwid.BoxAdapter(Console(self.core), height=1)
        self.console = self.footer.original_widget

    def set_contact_detail_meta(self, meta):
        pass
        #text = urwid.AttrMap(urwid.Text(meta, 'right'), 'status_bar')
        #self.set_footer(text)

    def clear_footer(self):
        self.footer = urwid.BoxAdapter(Console(self.core), height=1)
        self.console = self.footer.original_widget
        self.set_focus('body')


class ContactFrameColumns(urwid.Columns):
    def __init__(self, contact_list, core, config):
        self.core = core
        self.focus_map = config['display']['focus_map']
        self.nav_width = config['display']['nav_width']
        super(ContactFrameColumns, self).__init__([], dividechars=1)
        self.set_contact_list(contact_list)

    def set_contact_list(self, contact_list):
        self.contents.append((urwid.AttrMap(ContactList(contact_list, self.core),
            'options', self.focus_map), self.options('given', self.nav_width)))

    def set_contact_details(self, contact):
        self.contents.append((urwid.AttrMap(ContactDetails(contact, self.core),
            'options', self.focus_map), self.options('weight', 1, True)))

    def keypress(self, size, key):
        if key == 'ctrl r':
            self.core.frame.refresh_contact_list()
        else:
            return super(ContactFrameColumns, self).keypress(size, key)

    

class CustListBox(urwid.ListBox):
    def __init__(self, listwalker, core):
        super(CustListBox, self).__init__(listwalker)
        self.repeat_command = 0
        self.core = core

    def keypress(self, size, key):
        if key == 'esc':
            self.core.last_keypress = None
        if self.core.last_keypress == 'i':
            focused_contact = self.core.frame.contact_list.get_focused_contact()
            if key == 'i':
                self.core.last_keypress = None
                self.core.cli.add_attribute(focused_contact)
            elif key == 'g':
                self.core.last_keypress = None
                self.core.cli.add_gift(focused_contact)
            elif key == 'n':
                self.core.last_keypress = None
                self.core.cli.add_note(focused_contact)
            else:
                self.core.last_keypress = None
        else:
            if key == 'i':
                self.core.last_keypress = 'i'
            elif key == '/':
                self.core.cli.search_contact()
            elif key == 't':
                if self.repeat_command > 0:
                    self.jump_down(size, self.repeat_command)
                    self.repeat_command = 0
                else:
                    super(CustListBox, self).keypress(size, 'down')
            elif key == 'r':
                if self.repeat_command > 0:
                    self.jump_up(size, self.repeat_command)
                    self.repeat_command = 0
                else:
                    super(CustListBox, self).keypress(size, 'up')
            elif key == 'G':
                super(CustListBox, self).keypress(size, 'end')
                super(CustListBox, self).keypress(size, 'end')
            elif key == 'g':
                super(CustListBox, self).keypress(size, 'home')
            elif key in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                if self.repeat_command > 0:
                    self.repeat_command = int(str(self.repeat_command) + key)
                else:
                    self.repeat_command = int(key)
            else:
                return super(CustListBox, self).keypress(size, key)

    def jump_down(self, size, n):
        for i in range(0, n):
            super(CustListBox, self).keypress(size, 'down')

    def jump_up(self, size, n):
        for i in range(0, n):
            super(CustListBox, self).keypress(size, 'up')


class ContactList(CustListBox):
    def __init__(self, contact_list, core):
        listwalker = urwid.SimpleFocusListWalker([])
        super(ContactList, self).__init__(listwalker, core)
        self.core = core
        self.set(contact_list)

    def set(self, contact_list):
        a = []
        pos = 0
        for c in contact_list:
            entry = ContactEntry(c, pos, self.core)
            urwid.connect_signal(entry, 'click', self.core.frame.set_contact_details) #TODO in ListEntry
            a.append(entry)
            pos = pos + 1
        self.body = urwid.SimpleFocusListWalker(a)
        urwid.connect_signal(self.body, 'modified', self.core.frame.set_contact_details)

    def get_focused_contact(self):
        return self.focus.contact

    def set_focused_contact(self, contact):
        pos = self.get_contact_position(contact)
        self.set_focus(pos)

    def get_focus_position(self):
        return self.focus_position

    def set_focus_position(self, pos):
        self.focus_position = pos

    def get_contact_position(self, contact):
        pos = 0
        for entry in self.body:
            if entry.label == contact.name:
                return pos
            pos = pos + 1
        return None

    def get_contact_position_startswith(self, name):
        pos = 0
        for entry in self.body:
            if entry.label.startswith(name):
                return pos
            pos = pos + 1
        return None

    def jump_to_contact(self, name):
        pos = self.get_contact_position_startswith(name)
        if pos is not None:
            self.set_focus(pos)

    def keypress(self, size, key):
        if self.core.last_keypress is None:
            if key == 'n':
                # if has details
                if self.core.frame.contact_details.number_of_details() > 0:
                    return super(ContactList, self).keypress(size, 'right')
                else:
                    return super(ContactList, self).keypress(size, key)
            else:
                return super(ContactList, self).keypress(size, key)
        else:
            return super(ContactList, self).keypress(size, key)


class ContactDetails(CustListBox):
    def __init__(self, contact, core):
        listwalker = urwid.SimpleFocusListWalker([])
        super(ContactDetails, self).__init__(listwalker, core)
        self.core = core
        self.set(contact)

    def set(self, contact):
        entries = [urwid.Text(contact.name), urwid.Divider()]

        if contact.attributes is not None:
            for a in contact.attributes:
                entries.append(AttributeEntry(contact, Attribute(a[0], a[1]), self.core))

        if contact.gifts is not None:
            if len(entries) > 2:
                entries.append(urwid.Divider())
            entries.append(urwid.Text(u"GESCHENKE"))
            for a in contact.gifts:
                entries.append(GiftEntry(contact, Gift(a), self.core))

        if contact.notes is not None:
            if len(entries) > 2:
                entries.append(urwid.Divider())
            entries.append(urwid.Text(u"NOTIZEN"))
            for d, content in contact.notes.items():
                date = datetime.strptime(d, '%Y%m%d')
                entries.append(NoteEntry(contact, Note(date, content), self.core))

        self.body = urwid.SimpleFocusListWalker(entries)
        urwid.connect_signal(self.body, 'modified', self.show_meta)

    def show_meta(self):
        if isinstance(self.focus, NoteEntry):
            date = datetime.strftime(self.focus.note.date, '%d-%m-%Y')
            self.core.frame.set_contact_detail_meta(date)
        else:
            self.core.frame.clear_footer()

    def number_of_details(self):
        return len(self.body) - 2

    def keypress(self, size, key):
        if key == 'd':
            return super(ContactDetails, self).keypress(size, 'left')
        else:
            return super(ContactDetails, self).keypress(size, key)


class ListEntry(urwid.Button):
    def __init__(self, label, core):
        super(ListEntry, self).__init__(label)
        self.core = core
        self.set_label(label)

    def set_label(self, label):
        super(ListEntry, self).set_label(label)
        cursor_pos = len(label) + 1
        self._w = urwid.AttrMap(urwid.SelectableIcon(
            label, cursor_pos), None, 'selected')


class ContactEntry(ListEntry):
    def __init__(self, contact, pos, core):
        super(ContactEntry, self).__init__(contact.name, core)
        self.contact = contact
        self.pos = pos

    def keypress(self, size, key):
        if self.core.last_keypress is None:
            if key == 'a':
                self.core.cli.rename_contact(self.contact, self.pos)
            elif key == 'I':
                self.core.cli.add_contact(self.pos)
            elif key == 'h':
                self.core.cli.delete_contact(self.contact, self.pos)
            else:
                return super(ContactEntry, self).keypress(size, key)
        else:
            return super(ContactEntry, self).keypress(size, key)


class DetailEntry(ListEntry):
    def __init__(self, contact, label, core):
        super(DetailEntry, self).__init__(label, core)
        self.contact = contact


class AttributeEntry(DetailEntry):
    def __init__(self, contact, attribute, core):
        label = attribute.key + ': ' + attribute.value
        super(AttributeEntry, self).__init__(contact, label, core)
        self.attribute = attribute

    def keypress(self, size, key):
        if key == 'a':
            self.core.cli.edit_attribute(self.contact, self.attribute)
        elif key == 'h':
            self.core.cli.delete_attribute(self.contact, self.attribute)
        elif key == 'y':
            pyperclip.copy(self.value)
            msg = "Copied \"" + self.attribute.value + "\" to clipboard."
            self.core.frame.show_message(msg)
        else:
            return super(ListEntry, self).keypress(size, key)

class GiftEntry(DetailEntry):
    def __init__(self, contact, gift, core):
        super(GiftEntry, self).__init__(contact, gift.name, core)
        self.gift = gift

    def keypress(self, size, key):
        if key == 'a':
            self.core.cli.edit_gift(self.contact, self.gift)
        elif key == 'h':
            self.core.cli.delete_gift(self.contact, self.gift)
        else:
            return super(GiftEntry, self).keypress(size, key)

class NoteEntry(DetailEntry):
    def __init__(self, contact, note, core):
        super(NoteEntry, self).__init__(contact, note.content, core)
        self.note = note

    def keypress(self, size, key):
        if key == 'enter':
            self.core.cli.edit_note(self.contact, self.note)
        elif key == 'a':
            self.core.cli.rename_note(self.contact, self.note)
        elif key == 'h':
            self.core.cli.delete_note(self.contact, self.note)
        else:
            return super(NoteEntry, self).keypress(size, key)

class Console(urwid.Filler):
    def __init__(self, core):
        super(Console, self).__init__(urwid.Text(""))
        self.core = core

    def show_console(self, command=''):
        self.body = urwid.Edit(":", command)
        self.core.frame.set_focus('footer')

    def show_message(self, message):
        self.body = urwid.Text(message)

    def show_input(self, request):
        self.body = urwid.Edit("{}?".format(request))
        self.core.frame.set_focus('footer')

    def show_search(self):
        self.body = urwid.Edit("/")
        self.core.frame.set_focus('footer')

    def keypress(self, size, key):
        if key == 'esc':
            self.core.frame.clear_footer()
        if key != 'enter':
            return super(Console, self).keypress(size, key)

        args = self.original_widget.edit_text.split()
        return self.core.cli.handle(args)


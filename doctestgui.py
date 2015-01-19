# -*- coding: utf-8 -*-
#
# Created Dec. 2014 by Douglas Thor
# Based on pylintgui.py: Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""doctest widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import with_statement, print_function

from spyderlib.qt.QtGui import (QHBoxLayout, QWidget,
                                QMessageBox, QVBoxLayout, QLabel, QFont)
from spyderlib.qt.QtCore import SIGNAL, QProcess, QByteArray, QTextCodec
locale_codec = QTextCodec.codecForLocale()
from spyderlib.qt.compat import getopenfilename

import sys
#import os
import os.path as osp
import time
#import subprocess

# Local imports
#from spyderlib import dependencies
from spyderlib.utils import programs
#from spyderlib.utils.encoding import to_unicode_from_fs
from spyderlib.utils.qthelpers import get_icon, create_toolbutton
from spyderlib.baseconfig import get_conf_path, get_translation
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.sourcecode import codeeditor
from spyderlib.widgets.comboboxes import (PythonModulesComboBox,
                                          is_module_or_package)
from spyderlib.py3compat import to_text_string, getcwd, pickle
_ = get_translation("p_doctest", dirname="spyderplugins")


DOCTEST_PATH = programs.find_program('doctest')


class ResultsWindow(QWidget):
    """
    Simple read-only editor that contains the doctest results.

    Will eventually replace with a something that lets the user click on
    a linenumber to be taken to that file.
    """
    def __init__(self, parent):
        """
        __init__(self, parent: QWidget) -> QWidget
        """
        QWidget.__init__(self, parent)
        self.editor = None
        self.filename = None
        self.results = None
        self.data = None
#        self.setWindowTitle("Hello")

        self.editor = codeeditor.CodeEditor(self)
        self.editor.setup_editor(linenumbers=False, language='py',
                                 scrollflagarea=False, edge_line=False)
        self.editor.set_font(QFont('Consolas'))

        self.connect(self.editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        self.editor.setReadOnly(True)

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)

    def clear_results(self):
        """ Remove the results from the screen """
        self.editor.clear()

    def set_results(self, filename, results):
        """ Set instance attributes for filename and results """
        self.filename = filename
        self.results = results
        self.refresh()

    def refresh(self):
        """ Refresh the widget, printing the results to the screen """
        self.editor.clear()
        self.data = self.results
        self.editor.set_text(self.data)


class DoctestWidget(QWidget):
    """
    doctest widget.
    """
    DATAPATH = get_conf_path('doctest.results')
    VERSION = '1.1.0'

    def __init__(self, parent, max_entries=100):
        QWidget.__init__(self, parent)

        self.setWindowTitle("Doctest")

        self.output = None
        self.error_output = None

        self.max_entries = max_entries
        self.rdata = []
        if osp.isfile(self.DATAPATH):
            try:
                data = pickle.loads(open(self.DATAPATH, 'rb').read())
                if data[0] == self.VERSION:
                    self.rdata = data[1:]
            except (EOFError, ImportError):
                pass

        self.filecombo = PythonModulesComboBox(self)
        if self.rdata:
            self.remove_obsolete_items()
            self.filecombo.addItems(self.get_filenames())

        self.start_button = create_toolbutton(self,
                                              icon=get_icon('run.png'),
                                              text=_("Analyze"),
                                              tip=_("Run analysis"),
                                              triggered=self.start,
                                              text_beside_icon=True)
        self.stop_button = create_toolbutton(self,
                                             icon=get_icon('stop.png'),
                                             text=_("Stop"),
                                             tip=_("Stop current analysis"),
                                             text_beside_icon=True)
        self.connect(self.filecombo, SIGNAL('valid(bool)'),
                     self.start_button.setEnabled)
        self.connect(self.filecombo, SIGNAL('valid(bool)'), self.show_data)

        browse_button = create_toolbutton(self,
                                          icon=get_icon('fileopen.png'),
                                          tip=_('Select Python file'),
                                          triggered=self.select_file)

        self.ratelabel = QLabel()
        self.datelabel = QLabel()
        self.log_button = create_toolbutton(self,
                                            icon=get_icon('log.png'),
                                            text=_("Output"),
                                            text_beside_icon=True,
                                            tip=_("Complete output"),
                                            triggered=self.show_log)
        self.resultswidget = ResultsWindow(self)

        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(self.filecombo)
        hlayout1.addWidget(browse_button)
        hlayout1.addWidget(self.start_button)
        hlayout1.addWidget(self.stop_button)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.ratelabel)
        hlayout2.addStretch()
        hlayout2.addWidget(self.datelabel)
        hlayout2.addStretch()
        hlayout2.addWidget(self.log_button)

        layout = QVBoxLayout()
        layout.addLayout(hlayout1)
        layout.addLayout(hlayout2)
        layout.addWidget(self.resultswidget)
        self.setLayout(layout)

        self.process = None
        self.set_running_state(False)

        self.show_data()

    def analyze(self, filename):
        """
        Run doctest analysis on the active file.
        """
        filename = to_text_string(filename)    # filename is a QString instance
        self.kill_if_running()
        index, _data = self.get_data(filename)
        if index is None:
            self.filecombo.addItem(filename)
            self.filecombo.setCurrentIndex(self.filecombo.count()-1)
        else:
            self.filecombo.setCurrentIndex(self.filecombo.findText(filename))
        self.filecombo.selected()
#        print("is valid? {}".format(self.filecombo.is_valid()))
        if self.filecombo.is_valid():
            self.start()

    def select_file(self):
        """ Select the file to run """
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename, _selfilter = getopenfilename(self,
                                               _("Select Python file"),
                                               getcwd(),
                                               _("Python files")+" (*.py ; *.pyw)")
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        if filename:
            self.analyze(filename)

    def remove_obsolete_items(self):
        """ Remove obsolete items from the data log"""
        self.rdata = [(filename, data) for filename, data in self.rdata
                      if is_module_or_package(filename)]

    def get_filenames(self):
        """ Get filenames that are in the data log """
        return [filename for filename, _data in self.rdata]

    def get_data(self, filename):
        """ Get data from the data log """
        filename = osp.abspath(filename)
        for index, (fname, data) in enumerate(self.rdata):
            if fname == filename:
                return index, data
        else:
            return None, None

    def set_data(self, filename, data):
        """ Set data in the data log """
        filename = osp.abspath(filename)
        index, _data = self.get_data(filename)
        if index is not None:
            self.rdata.pop(index)
        self.rdata.insert(0, (filename, data))
        self.save()

    def save(self):
        """ Save data to the data log """
        while len(self.rdata) > self.max_entries:
            self.rdata.pop(-1)
        pickle.dump([self.VERSION]+self.rdata, open(self.DATAPATH, 'wb'), 2)

    def show_log(self):
        print("Show Log was clicked! Doesn't do anything yet...")
        pass
#        if self.output:
#            TextEditor(self.output, title=_("Pylint output"),
#                       readonly=True, size=(700, 500)).exec_()

    def run_doctest(self, filename):
        """
        Actually runs doctest on the file
        """
        import doctest
        fail_count, test_count = doctest.testfile(filename)
        print(fail_count, test_count)

    def start(self):
        """
        Run doctest analisys.

        Calls ``doctest run <filepath>`` as a seperate thread.

        Redirects all standard output to the ``self.read_output()`` method.

        Upon finished signal, calls self.finished().
        """
        filename = to_text_string(self.filecombo.currentText())

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)
        self.process.setWorkingDirectory(osp.dirname(filename))
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.read_output)
        self.connect(self.process, SIGNAL("readyReadStandardError()"),
                     lambda: self.read_output(error=True))
        self.connect(self.process,
                     SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)
        self.connect(self.stop_button, SIGNAL("clicked()"),
                     self.process.kill)
#                     self.kill)

        self.output = ''
        self.error_output = ''

        # start the process which runs the doctest analysis.
        p_args = ['-m', 'doctest', filename, '-v']
        p_args = ['-m', 'doctest', filename]
        self.process.start('python', p_args)
        running = self.process.waitForStarted()
        self.set_running_state(running)
        if not running:
            QMessageBox.critical(self, _("Error"),
                                 _("Process failed to start"))

    def set_running_state(self, state=True):
        """ Sets the running state """
        self.start_button.setEnabled(not state)
        self.stop_button.setEnabled(state)

    def read_output(self, error=False):
        """
        Reads the output, both standard and error, to instance attributes
        """
        if error:
            self.process.setReadChannel(QProcess.StandardError)
        else:
            self.process.setReadChannel(QProcess.StandardOutput)

        qba = QByteArray()
        while self.process.bytesAvailable():
            if error:
                qba += self.process.readAllStandardError()
            else:
                qba += self.process.readAllStandardOutput()
        text = to_text_string(locale_codec.toUnicode(qba.data()))
        if error:
            self.error_output += text
        else:
            self.output += text

    def finished(self):
        """ Processes the finish state """
        self.set_running_state(False)
        if not self.output:
            # Make a note that everything ran just fine
            self.output = "No Doctest Errors"
        if not self.output:
            if self.error_output:
                QMessageBox.critical(self, _("Error"), self.error_output)
                print("doctest error:\n\n" + self.error_output,
                      file=sys.stderr)
            return

        filename = to_text_string(self.filecombo.currentText())
        self.set_data(filename, (time.localtime(), self.output))
        self.output = self.error_output + self.output
        self.show_data(justanalyzed=True)

    def kill_if_running(self):
        """ Kills the process if it's running """
        if self.process is not None:
            if self.process.state() == QProcess.Running:
                self.process.kill()
                self.process.waitForFinished()

    def show_data(self, justanalyzed=False):
        """ Shows the data """
        if not justanalyzed:
            self.output = None
        self.log_button.setEnabled(self.output is not None
                                   and len(self.output) > 0)
        self.kill_if_running()
        filename = to_text_string(self.filecombo.currentText())
        if not filename:
            return

        _index, data = self.get_data(filename)
        if data is None:
            text = _('Source code has not been rated yet.')
            self.resultswidget.clear_results()
            date_text = ''
#            text = ''
#            datetime, results = data
#            text_style = "<span style=\'color: #444444\'><b>%s </b></span>"
#            self.resultswidget.set_results(filename, results)
#            date = to_text_string(time.strftime("%d %b %Y %H:%M",
#                                                datetime),
#                                  encoding='utf8')
#            date_text = text_style % date
        else:
            text = ''
            datetime, results = data
            text_style = "<span style=\'color: #444444\'><b>%s </b></span>"
            self.resultswidget.set_results(filename, results)
            date = to_text_string(time.strftime("%d %b %Y %H:%M",
                                                datetime),
                                  encoding='utf8')
            date_text = text_style % date

        self.ratelabel.setText(text)
        self.datelabel.setText(date_text)


def test():
    """Run doctest widget test"""
    path = osp.join(osp.split(__file__)[0], "test_doctestgui.py")
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = DoctestWidget(None)
    widget.show()
    widget.analyze(path)
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()

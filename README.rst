spyder-doctest-plugin
======================

A Spyder plugin for the built-in ``doctest`` package.

Installation
------------

1.  Put p_doctest.py in ``%pythonpath%\Lib\site-packages\spyderplugins``
2.  Put doctestgui.py in
    ``%pythonpath%\Lib\site-packages\spyderplugins\widgets``
3.  (Optional) put test_doctestgui.py in
    ``%pythonpath%\Lib\site-packages\spyderplugins\widgets``
4.  Load up spyder. It *should* work.


Usage
-----

With the file open that you want to run coverage on, press
``ALT`` + ``F12``.

Requires
--------

1.  It's a plugin for Spyder, so... you need
    Spyder_. I've tested it with Spyder 2.3.2 and Python 2.7.6. Additional
    testing is appreciated.


.. _Spyder: https://code.google.com/p/spyderlib/

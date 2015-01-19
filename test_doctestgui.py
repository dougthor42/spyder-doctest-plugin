# -*- coding: utf-8 -*-
"""
Test cases for the doctestgui.py file.
"""

from __future__ import print_function, division
#from __future__ import absolute_import
#from __future__ import unicode_literals

__author__ = "Douglas Thor"
__version__ = "v0.1.0"


def func1(a, b):
    """
    >>> func1(1, 1)
    2
    >>> func1(3, 5)
    8
    """
    return a + b


def func2(a):
    """
    >>> func2(1)
    1
    >>> func2(2)
    4
    >>> func2(3)
    9
    >>> func2(-1)
    0
    """
    if a <= 0:
        return 0
    else:
        return a**2


def main():
    """ Main Code """
    print("test_doctestgui.py has been run")
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    main()

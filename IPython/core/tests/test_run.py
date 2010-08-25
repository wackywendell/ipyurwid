"""Tests for code execution (%run and related), which is particularly tricky.

Because of how %run manages namespaces, and the fact that we are trying here to
verify subtle object deletion and reference counting issues, the %run tests
will be kept in this separate file.  This makes it easier to aggregate in one
place the tricks needed to handle it; most other magics are much easier to test
and we do so in a common test_magic file.
"""
from __future__ import absolute_import

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import os
import sys
import tempfile

import nose.tools as nt

from IPython.testing import decorators as dec
from IPython.testing import tools as tt

#-----------------------------------------------------------------------------
# Test functions begin
#-----------------------------------------------------------------------------

def doctest_refbug():
    """Very nasty problem with references held by multiple runs of a script.
    See: https://bugs.launchpad.net/ipython/+bug/269966

    In [1]: _ip.clear_main_mod_cache()
    # random
    
    In [2]: %run refbug

    In [3]: call_f()
    lowercased: hello

    In [4]: %run refbug

    In [5]: call_f()
    lowercased: hello
    lowercased: hello
    """


def doctest_run_builtins():
    r"""Check that %run doesn't damage __builtins__.

    In [1]: import tempfile

    In [2]: bid1 = id(__builtins__)

    In [3]: fname = tempfile.mkstemp('.py')[1]

    In [3]: f = open(fname,'w')

    In [4]: f.write('pass\n')

    In [5]: f.flush()

    In [6]: t1 = type(__builtins__)

    In [7]: %run $fname

    In [7]: f.close()

    In [8]: bid2 = id(__builtins__)

    In [9]: t2 = type(__builtins__)

    In [10]: t1 == t2
    Out[10]: True

    In [10]: bid1 == bid2
    Out[10]: True

    In [12]: try:
       ....:     os.unlink(fname)
       ....: except:
       ....:     pass
       ....: 
    """

# For some tests, it will be handy to organize them in a class with a common
# setup that makes a temp file

class TestMagicRunPass(tt.TempFileMixin):

    def setup(self):
        """Make a valid python temp file."""
        self.mktmp('pass\n')

    def run_tmpfile(self):
        _ip = get_ipython()
        # This fails on Windows if self.tmpfile.name has spaces or "~" in it.
        # See below and ticket https://bugs.launchpad.net/bugs/366353
        _ip.magic('run %s' % self.fname)

    def test_builtins_id(self):
        """Check that %run doesn't damage __builtins__ """
        _ip = get_ipython()
        # Test that the id of __builtins__ is not modified by %run
        bid1 = id(_ip.user_ns['__builtins__'])
        self.run_tmpfile()
        bid2 = id(_ip.user_ns['__builtins__'])
        tt.assert_equals(bid1, bid2)

    def test_builtins_type(self):
        """Check that the type of __builtins__ doesn't change with %run.
        
        However, the above could pass if __builtins__ was already modified to
        be a dict (it should be a module) by a previous use of %run.  So we
        also check explicitly that it really is a module:
        """
        _ip = get_ipython()
        self.run_tmpfile()
        tt.assert_equals(type(_ip.user_ns['__builtins__']),type(sys))

    def test_prompts(self):
        """Test that prompts correctly generate after %run"""
        self.run_tmpfile()
        _ip = get_ipython()
        p2 = str(_ip.displayhook.prompt2).strip()
        nt.assert_equals(p2[:3], '...')


class TestMagicRunSimple(tt.TempFileMixin):

    def test_simpledef(self):
        """Test that simple class definitions work."""
        src = ("class foo: pass\n"
               "def f(): return foo()")
        self.mktmp(src)
        _ip.magic('run %s' % self.fname)
        _ip.runlines('t = isinstance(f(), foo)')
        nt.assert_true(_ip.user_ns['t'])

    # We have to skip these in win32 because getoutputerr() crashes,
    # due to the fact that subprocess does not support close_fds when
    # redirecting stdout/err.  So unless someone who knows more tells us how to
    # implement getoutputerr() in win32, we're stuck avoiding these.
    @dec.skip_win32
    def test_obj_del(self):
        """Test that object's __del__ methods are called on exit."""
        
        # This test is known to fail on win32.
        # See ticket https://bugs.launchpad.net/bugs/366334
        src = ("class A(object):\n"
               "    def __del__(self):\n"
               "        print 'object A deleted'\n"
               "a = A()\n")
        self.mktmp(src)
        tt.ipexec_validate(self.fname, 'object A deleted')

    @dec.skip_win32
    def test_tclass(self):
        mydir = os.path.dirname(__file__)
        tc = os.path.join(mydir, 'tclass')
        src = ("%%run '%s' C-first\n"
               "%%run '%s' C-second\n") % (tc, tc)
        self.mktmp(src, '.ipy')
        out = """\
ARGV 1-: ['C-first']
ARGV 1-: ['C-second']
tclass.py: deleting object: C-first
"""
        tt.ipexec_validate(self.fname, out)

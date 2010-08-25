import inspect
import re
import sys
from subprocess import Popen, PIPE

from IPython.core.interactiveshell import (
    InteractiveShell, InteractiveShellABC
)
from IPython.core.displayhook import DisplayHook
from IPython.core.macro import Macro
from IPython.utils.io import rprint
from IPython.utils.path import get_py_filename
from IPython.utils.text import StringTypes
from IPython.utils.traitlets import Instance, Type, Dict
from IPython.utils.warn import warn
from IPython.zmq.session import extract_header
from IPython.core.payloadpage import install_payload_page


# Install the payload version of page.
install_payload_page()


class ZMQDisplayHook(DisplayHook):

    session = Instance('IPython.zmq.session.Session')
    pub_socket = Instance('zmq.Socket')
    parent_header = Dict({})

    def set_parent(self, parent):
        """Set the parent for outbound messages."""
        self.parent_header = extract_header(parent)

    def start_displayhook(self):
        self.msg = self.session.msg(u'pyout', {}, parent=self.parent_header)

    def write_output_prompt(self):
        """Write the output prompt."""
        if self.do_full_cache:
            self.msg['content']['output_sep'] = self.output_sep
            self.msg['content']['prompt_string'] = str(self.prompt_out)
            self.msg['content']['prompt_number'] = self.prompt_count
            self.msg['content']['output_sep2'] = self.output_sep2

    def write_result_repr(self, result_repr):
        self.msg['content']['data'] = result_repr

    def finish_displayhook(self):
        """Finish up all displayhook activities."""
        self.pub_socket.send_json(self.msg)
        self.msg = None


class ZMQInteractiveShell(InteractiveShell):
    """A subclass of InteractiveShell for ZMQ."""

    displayhook_class = Type(ZMQDisplayHook)

    def system(self, cmd):
        cmd = self.var_expand(cmd, depth=2)
        sys.stdout.flush()
        sys.stderr.flush()
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        for line in p.stdout.read().split('\n'):
            if len(line) > 0:
                print line
        for line in p.stderr.read().split('\n'):
            if len(line) > 0:
                print line
        p.wait()

    def init_io(self):
        # This will just use sys.stdout and sys.stderr. If you want to
        # override sys.stdout and sys.stderr themselves, you need to do that
        # *before* instantiating this class, because Term holds onto 
        # references to the underlying streams.
        import IPython.utils.io
        Term = IPython.utils.io.IOTerm()
        IPython.utils.io.Term = Term

    def magic_edit(self,parameter_s='',last_call=['','']):
        """Bring up an editor and execute the resulting code.

        Usage:
          %edit [options] [args]

        %edit runs IPython's editor hook.  The default version of this hook is
        set to call the __IPYTHON__.rc.editor command.  This is read from your
        environment variable $EDITOR.  If this isn't found, it will default to
        vi under Linux/Unix and to notepad under Windows.  See the end of this
        docstring for how to change the editor hook.

        You can also set the value of this editor via the command line option
        '-editor' or in your ipythonrc file. This is useful if you wish to use
        specifically for IPython an editor different from your typical default
        (and for Windows users who typically don't set environment variables).

        This command allows you to conveniently edit multi-line code right in
        your IPython session.
        
        If called without arguments, %edit opens up an empty editor with a
        temporary file and will execute the contents of this file when you
        close it (don't forget to save it!).


        Options:

        -n <number>: open the editor at a specified line number.  By default,
        the IPython editor hook uses the unix syntax 'editor +N filename', but
        you can configure this by providing your own modified hook if your
        favorite editor supports line-number specifications with a different
        syntax.
        
        -p: this will call the editor with the same data as the previous time
        it was used, regardless of how long ago (in your current session) it
        was.

        -r: use 'raw' input.  This option only applies to input taken from the
        user's history.  By default, the 'processed' history is used, so that
        magics are loaded in their transformed version to valid Python.  If
        this option is given, the raw input as typed as the command line is
        used instead.  When you exit the editor, it will be executed by
        IPython's own processor.
        
        -x: do not execute the edited code immediately upon exit. This is
        mainly useful if you are editing programs which need to be called with
        command line arguments, which you can then do using %run.


        Arguments:

        If arguments are given, the following possibilites exist:

        - The arguments are numbers or pairs of colon-separated numbers (like
        1 4:8 9). These are interpreted as lines of previous input to be
        loaded into the editor. The syntax is the same of the %macro command.

        - If the argument doesn't start with a number, it is evaluated as a
        variable and its contents loaded into the editor. You can thus edit
        any string which contains python code (including the result of
        previous edits).

        - If the argument is the name of an object (other than a string),
        IPython will try to locate the file where it was defined and open the
        editor at the point where it is defined. You can use `%edit function`
        to load an editor exactly at the point where 'function' is defined,
        edit it and have the file be executed automatically.

        If the object is a macro (see %macro for details), this opens up your
        specified editor with a temporary file containing the macro's data.
        Upon exit, the macro is reloaded with the contents of the file.

        Note: opening at an exact line is only supported under Unix, and some
        editors (like kedit and gedit up to Gnome 2.8) do not understand the
        '+NUMBER' parameter necessary for this feature. Good editors like
        (X)Emacs, vi, jed, pico and joe all do.

        - If the argument is not found as a variable, IPython will look for a
        file with that name (adding .py if necessary) and load it into the
        editor. It will execute its contents with execfile() when you exit,
        loading any code in the file into your interactive namespace.

        After executing your code, %edit will return as output the code you
        typed in the editor (except when it was an existing file). This way
        you can reload the code in further invocations of %edit as a variable,
        via _<NUMBER> or Out[<NUMBER>], where <NUMBER> is the prompt number of
        the output.

        Note that %edit is also available through the alias %ed.

        This is an example of creating a simple function inside the editor and
        then modifying it. First, start up the editor:

        In [1]: ed
        Editing... done. Executing edited code...
        Out[1]: 'def foo():n    print "foo() was defined in an editing session"n'

        We can then call the function foo():
        
        In [2]: foo()
        foo() was defined in an editing session

        Now we edit foo.  IPython automatically loads the editor with the
        (temporary) file where foo() was previously defined:
        
        In [3]: ed foo
        Editing... done. Executing edited code...

        And if we call foo() again we get the modified version:
        
        In [4]: foo()
        foo() has now been changed!

        Here is an example of how to edit a code snippet successive
        times. First we call the editor:

        In [5]: ed
        Editing... done. Executing edited code...
        hello
        Out[5]: "print 'hello'n"

        Now we call it again with the previous output (stored in _):

        In [6]: ed _
        Editing... done. Executing edited code...
        hello world
        Out[6]: "print 'hello world'n"

        Now we call it with the output #8 (stored in _8, also as Out[8]):

        In [7]: ed _8
        Editing... done. Executing edited code...
        hello again
        Out[7]: "print 'hello again'n"


        Changing the default editor hook:

        If you wish to write your own editor hook, you can put it in a
        configuration file which you load at startup time.  The default hook
        is defined in the IPython.core.hooks module, and you can use that as a
        starting example for further modifications.  That file also has
        general instructions on how to set a new hook for use once you've
        defined it."""
        
        # FIXME: This function has become a convoluted mess.  It needs a
        # ground-up rewrite with clean, simple logic.

        def make_filename(arg):
            "Make a filename from the given args"
            try:
                filename = get_py_filename(arg)
            except IOError:
                if args.endswith('.py'):
                    filename = arg
                else:
                    filename = None
            return filename

        # custom exceptions
        class DataIsObject(Exception): pass

        opts,args = self.parse_options(parameter_s,'prn:')
        # Set a few locals from the options for convenience:
        opts_p = opts.has_key('p')
        opts_r = opts.has_key('r')
        
        # Default line number value
        lineno = opts.get('n',None)
        if lineno is not None:
            try:
                lineno = int(lineno)
            except:
                warn("The -n argument must be an integer.")
                return

        if opts_p:
            args = '_%s' % last_call[0]
            if not self.shell.user_ns.has_key(args):
                args = last_call[1]
            
        # use last_call to remember the state of the previous call, but don't
        # let it be clobbered by successive '-p' calls.
        try:
            last_call[0] = self.shell.displayhook.prompt_count
            if not opts_p:
                last_call[1] = parameter_s
        except:
            pass

        # by default this is done with temp files, except when the given
        # arg is a filename
        use_temp = 1

        if re.match(r'\d',args):
            # Mode where user specifies ranges of lines, like in %macro.
            # This means that you can't edit files whose names begin with
            # numbers this way. Tough.
            ranges = args.split()
            data = ''.join(self.extract_input_slices(ranges,opts_r))
        elif args.endswith('.py'):
            filename = make_filename(args)
            data = ''
            use_temp = 0
        elif args:
            try:
                # Load the parameter given as a variable. If not a string,
                # process it as an object instead (below)

                #print '*** args',args,'type',type(args)  # dbg
                data = eval(args,self.shell.user_ns)
                if not type(data) in StringTypes:
                    raise DataIsObject

            except (NameError,SyntaxError):
                # given argument is not a variable, try as a filename
                filename = make_filename(args)
                if filename is None:
                    warn("Argument given (%s) can't be found as a variable "
                         "or as a filename." % args)
                    return

                data = ''
                use_temp = 0
            except DataIsObject:

                # macros have a special edit function
                if isinstance(data,Macro):
                    self._edit_macro(args,data)
                    return
                                
                # For objects, try to edit the file where they are defined
                try:
                    filename = inspect.getabsfile(data)
                    if 'fakemodule' in filename.lower() and inspect.isclass(data):                     
                        # class created by %edit? Try to find source
                        # by looking for method definitions instead, the
                        # __module__ in those classes is FakeModule.
                        attrs = [getattr(data, aname) for aname in dir(data)]
                        for attr in attrs:
                            if not inspect.ismethod(attr):
                                continue
                            filename = inspect.getabsfile(attr)
                            if filename and 'fakemodule' not in filename.lower():
                                # change the attribute to be the edit target instead
                                data = attr 
                                break
                    
                    datafile = 1
                except TypeError:
                    filename = make_filename(args)
                    datafile = 1
                    warn('Could not find file where `%s` is defined.\n'
                         'Opening a file named `%s`' % (args,filename))
                # Now, make sure we can actually read the source (if it was in
                # a temp file it's gone by now).
                if datafile:
                    try:
                        if lineno is None:
                            lineno = inspect.getsourcelines(data)[1]
                    except IOError:
                        filename = make_filename(args)
                        if filename is None:
                            warn('The file `%s` where `%s` was defined cannot '
                                 'be read.' % (filename,data))
                            return
                use_temp = 0
        else:
            data = ''

        if use_temp:
            filename = self.shell.mktempfile(data)
            print 'IPython will make a temporary file named:',filename

        payload = {
            'source' : 'IPython.zmq.zmqshell.ZMQInteractiveShell.edit_magic',
            'filename' : filename,
            'line_number' : lineno
        }
        self.payload_manager.write_payload(payload)


    def _showtraceback(self, etype, evalue, stb):

        exc_content = {
            u'status' : u'error',
            u'traceback' : stb,
            u'ename' : unicode(etype.__name__),
            u'evalue' : unicode(evalue)
        }

        dh = self.displayhook
        exc_msg = dh.session.msg(u'pyerr', exc_content, dh.parent_header)
        # Send exception info over pub socket for other clients than the caller
        # to pick up
        dh.pub_socket.send_json(exc_msg)

        # FIXME - Hack: store exception info in shell object.  Right now, the
        # caller is reading this info after the fact, we need to fix this logic
        # to remove this hack.
        self._reply_content = exc_content
        # /FIXME
        
        return exc_content

    def runlines(self, lines, clean=False):
        return InteractiveShell.runlines(self, lines, clean)

InteractiveShellABC.register(ZMQInteractiveShell)

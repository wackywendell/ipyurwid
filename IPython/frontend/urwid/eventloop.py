import Queue, time, heapq

from IPython.zmq.session import Message
from IPython.zmq.kernelmanager import (KernelManager, ZmqSocketChannel,
        XReqSocketChannel, SubSocketChannel, RepSocketChannel)
import urwid
from urwid import SelectEventLoop, ExitMainLoop
from IPython.utils.traitlets import Type
import select

def prettymessage(msg, indent=''):
    lines = []
    for k,v in dict(msg).items():
        if isinstance(v, Message):
            lines.append(indent + k)
            lines.extend(prettymessage(v, indent + '  '))
        else:
            lines.append('{0}{1:10}: {2}'.format(
                indent, k, repr(v)))
    return lines

class UrwidChannel(ZmqSocketChannel):
    def __init__(self, rcvd_queue, *args, **kwargs):
        super(UrwidChannel, self).__init__(*args, **kwargs)
        self.rcvd_queue = rcvd_queue

    def call_handlers(self, msg):
        self.rcvd_queue.put(msg)

class UrwidXReq(UrwidChannel, XReqSocketChannel):
    pass

class UrwidSub(UrwidChannel, SubSocketChannel):
    pass

class UrwidRep(UrwidChannel, RepSocketChannel):
    pass

class QueueKernelManager(KernelManager):
    xreq_channel_class = Type(UrwidXReq)
    sub_channel_class = Type(UrwidSub)
    rep_channel_class = Type(UrwidRep)
    
    def __init__(self, *args, **kw):
        super(QueueKernelManager, self).__init__(*args, **kw)
        self.rcvd_queue = Queue.Queue()

    @property
    def xreq_channel(self):
        """Get the REQ socket channel object to make requests of the kernel."""
        if self._xreq_channel is None:
            self._xreq_channel = self.xreq_channel_class(self.rcvd_queue,
                                                         self.context, 
                                                         self.session,
                                                         self.xreq_address)
        return self._xreq_channel

    @property
    def sub_channel(self):
        """Get the SUB socket channel object."""
        if self._sub_channel is None:
            self._sub_channel = self.sub_channel_class(self.rcvd_queue,
                                                       self.context,
                                                       self.session,
                                                       self.sub_address)
        return self._sub_channel

    @property
    def rep_channel(self):
        """Get the REP socket channel object to handle stdin (raw_input)."""
        if self._rep_channel is None:
            self._rep_channel = self.rep_channel_class(self.rcvd_queue,
                                                       self.context, 
                                                       self.session,
                                                       self.rep_address)
        return self._rep_channel


class IpyEventLoop(SelectEventLoop):
    """A simple event loop for use with ipython."""
    def __init__(self, queue, interp):
        self.queue = queue
        self.interp = interp
        super(IpyEventLoop, self).__init__()
    
    def _run_alarms(self):
        """Checks if there are any alarms that went off,
        and calls their callbacks if necessary"""
        curtime = time.time()
        if self._alarms and self._alarms[0][0] < curtime:
            tm, callback = heapq.heappop(self._alarms)
            callback()
            self._did_something = True
    
    def _run_msgs(self):
        """Checks if a message is in the queue, and runs it if there is"""
        try:
            msg = self.queue.get_nowait()
        except Queue.Empty:
            return
        
        self._did_something = True
        if not isinstance(msg, Message):
            msg = Message(msg)
        if hasattr(self.interp, msg.msg_type):
            func = getattr(self.interp, msg.msg_type)
        else:
            func = self.interp.unknown_msg
        func(msg)

    def _loop(self):
        self._did_something = False
        # Check for alarms
        self._run_alarms()

        # if there are any messages, gather and process them
        self._run_msgs()
        
        # check the file descriptors
        fds = self._watch_files.keys()
        
        # TODO: We can't select on fds and on queues.
        # I don't know how to fix this, which means that for
        # now this loop can't block.
        # I guess I could have another thread that blocks on
        # file descriptors, and adds them to a queue when
        # they go... but that seems inefficient.
        tm = 0.05 if not self._did_something else 0
        ready, w, err = select.select(fds, [], fds, tm)
        if not ready:
            if not self._did_something:
                self._enter_idle()
            self._did_something = False
        else:
            for fd in ready:
                callback = self._watch_files[fd]
                callback()
                self._did_something = True


class IpyInterpreter(object):
    def __init__(self, widget, screen, kernelmanager):
        self.widget = widget
        self.screen = screen
        self.kernelmanager = kernelmanager

    def _accept_input(self):
        """Accept the input from the input box and process it"""
        input = self.widget.input_text
        self.widget.input_text = u''
        input = input.strip()

        if input == u'':
            return True
        elif input == u'quit':
            raise ExitMainLoop()
        
        else:
            self.kernelmanager.xreq_channel.execute(input)
        #markup = self.widget.highlight(input)
        #self.widget.add_to_output(markup)
        return True

    def handle_input(self, input):
        """Handle unhandled keystrokes from urwid"""
        if input == 'enter':
            return self._accept_input()

    def execute_reply(self, msg):
        if msg.content.status == 'ok':
            if 'transformed_code' in msg.content:
                output = msg.content.transformed_code
                markup = self.widget.highlight(output)
                self.widget.add_to_output(markup)
        elif msg.content.status == 'error':
            self.widget.add_to_output('error: ' + str(msg.content))
            return
            errname = msg.content.exc_name
            errstr = msg.content.exc_str
            traceback = msg.content.traceback
            self.widget.add_to_output("\n".join(
                traceback + '{0}: {1}'.format(errname, errstr)))
        elif msg.content.status == 'abort':
            self.widget.add_to_output('Kernel abort')

    def pyin(self, msg):
        self.widget.add_to_output('pyin: ' + msg.content.code)

    def pyout(self, msg):
        self.widget.add_to_output('pyout [{0:2d}]: {1}'.format(
            msg.content.prompt_number, msg.content.data))

    def stream(self, msg):
        self.widget.add_to_output(u'stream:' + unicode(msg.content.data))




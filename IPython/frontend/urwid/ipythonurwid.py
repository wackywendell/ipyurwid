from interpreterwidget import InterpreterWidget, PagerScreen
from eventloop import QueueKernelManager, IpyEventLoop, IpyInterpreter
from urwid import MainLoop

def main():
    kern = QueueKernelManager()
    kern.start_kernel()
    kern.start_channels()
    queue = kern.rcvd_queue

    widget = InterpreterWidget()
    screen = PagerScreen()
    interp = IpyInterpreter(widget, screen, kern)

    eventloop = IpyEventLoop(queue, interp)

    mainloop = MainLoop(widget,
            unhandled_input = interp.handle_input, 
            event_loop = eventloop)

    try:
        mainloop.run()
    except:
        try:
            kern.stop_channels()
            kern.kill_kernel()
        except RuntimeError:
            pass
        raise

if __name__ == '__main__':
    main()

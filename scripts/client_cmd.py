#!/usr/bin/env python
import logging
import sys
import traceback
import katcp
import readline
from optparse import OptionParser
from cmd2 import Cmd
from src.utils import StreamClient

logging.basicConfig(level=logging.INFO,
                    stream=sys.stderr,
                    format="%(asctime)s - %(name)s - %(filename)s:"
                    "%(lineno)s - %(levelname)s - %(message)s")

log = logging.getLogger("reynard.basic_cli")


class KatcpCli(Cmd):
    """
    @brief      Basic command line interface to KATCP device

    @detail     This class provides a command line interface to
                to any katcp.DeviceClient subclass. Behaviour of the
                interface is determined by the client object passed
                at instantiation.
    """
    Cmd.shortcuts.update({'?': 'katcp'})
    Cmd.allow_cli_args = False
    def __init__(self,host,port,*args,**kwargs):
        """
        @brief  Instantiate new KatcpCli instance

        @params client A DeviceClient instance
        """
        self.host = host
        self.port = port
        self.katcp_parser = katcp.MessageParser()
        self.start_client()
        Cmd.__init__(self, *args, **kwargs)

    def start_client(self):
        log.info("Client connecting to port {self.host}:{self.port}".format(**locals()))
        self.client = StreamClient(self.host, self.port)
        self.client.start()
        self.prompt = "(katcp CLI {self.host}:{self.port}): ".format(**locals())

    def stop_client(self):
        self.client.stop()
        self.client.join()

    def do_katcp(self, arg, opts=None):
        """
        @brief      Send a request message to a katcp server

        @param      arg   The katcp formatted request
        """
        request = "?" + "".join(arg)
        log.info("Request: %s"%request)
        try:
            msg = self.katcp_parser.parse(request)
            self.client.ioloop.add_callback(self.client.send_message, msg)
        except Exception, e:
            e_type, e_value, trace = sys.exc_info()
            reason = "\n".join(traceback.format_exception(
                e_type, e_value, trace, 20))
            log.exception(reason)

    def do_connect(self, arg, opts=None):
        """
        @brief      Connect to different KATCP server

        @param      arg   Target server address in form "host:port"
        """
        try:
            host,port = arg.split(":")
        except Exception:
            print "Usage: connect <host>:<port>"
            return
        try:
            app = KatcpCli(host,port)
            app.cmdloop()
        except Exception as error:
            log.exception("Error from CLI")
        finally:
            app.stop_client()


if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-a', '--host', dest='host', type="string", default="", metavar='HOST',
                      help='attach to server HOST (default="" - localhost)')
    parser.add_option('-p', '--port', dest='port', type=int, default=1235, metavar='N',
                      help='attach to server port N (default=1235)')
    (opts, args) = parser.parse_args()
    sys.argv = sys.argv[:1]
    log.info("Ctrl-C to terminate.")
    try:
        app = KatcpCli(opts.host,opts.port)
        app.cmdloop()
    except Exception as error:
        log.exception("Error from CLI")
    finally:
        app.stop_client()
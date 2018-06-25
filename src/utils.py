import re
import codecs
import sys
from katcp import DeviceClient

"""
This regex is used to resolve escaped characters
in KATCP messages
"""
ESCAPE_SEQUENCE_RE = re.compile(r'''
    ( \\U........      # 8-digit hex escapes
    | \\u....          # 4-digit hex escapes
    | \\x..            # 2-digit hex escapes
    | \\[0-7]{1,3}     # Octal escapes
    | \\N\{[^}]+\}     # Unicode characters by name
    | \\[\\'"abfnrtv]  # Single-character escapes
    )''', re.UNICODE | re.VERBOSE)

def decode_katcp_message(s):
    """
    @brief      Render a katcp message human readable
    @params s   A string katcp message
    """
    def decode_match(match):
        return codecs.decode(match.group(0), 'unicode-escape')
    return ESCAPE_SEQUENCE_RE.sub(decode_match, s).replace("\_"," ")


class StreamClient(DeviceClient):
    def __init__(self,server_host, server_port,*args,**kwargs):
        self.stream = kwargs.get("stream",sys.stdout)
        super(StreamClient,self).__init__(server_host, server_port)

    def to_stream(self,prefix,msg):
        self.stream.write("%s:\n%s\n"%(prefix,decode_katcp_message(msg.__str__())))

    def unhandled_reply(self,msg):
        """Deal with unhandled replies"""
        self.to_stream("Unhandled reply",msg)

    def unhandled_inform(self,msg):
        """Deal with unhandled replies"""
        self.to_stream("Unhandled inform",msg)

    def unhandled_request(self,msg):
        """Deal with unhandled replies"""
        self.to_stream("Unhandled request",msg)
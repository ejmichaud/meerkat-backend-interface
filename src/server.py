r"""
Adapted from the reynard package (MIT license) on June 22, 2018: 
https://github.com/ewanbarr/reynard

  ___              _   _   _                      _      _    _    _            
 | _ )_ _ ___ __ _| |_| |_| |_  _ _ ___ _  _ __ _| |_   | |  (_)__| |_ ___ _ _  
 | _ \ '_/ -_) _` | / /  _| ' \| '_/ _ \ || / _` | ' \  | |__| (_-<  _/ -_) ' \ 
 |___/_| \___\__,_|_\_\\__|_||_|_| \___/\_,_\__, |_||_| |____|_/__/\__\___|_||_|
                                            |___/                               

            ______________                      ,-.
           /             /|                    / \  `.  __..-,O
          /             / |                   :   \ --''_..-'.'
         /____________ /  |                   |    . .-' `. '.
        | ___________ |   |                   :     .     .`.'
        ||           ||   |                    \     `.  /  .. 
        ||           ||   |                     \      `.   ' .
        ||           ||   |                      `,       `.   \
        ||___________||   |                     ,|,`.        `-.\
        |   _______   |  /                     '.||  ``-...__..-`
       /|  (_______)  | /____________           |  |
      ( |_____________|/             \          |__|
       \                              \         /||\
   .=======================.           \       //||\\
   | ::::::::::::::::  ::: |            \     // || \\        
   | ::::::::::::::[]  ::: |             \___//__||__\\___
   |   -----------     ::: |              '--------------'
   \-----------------------  
"""


import logging
import socket
import json
from tornado.gen import coroutine
from katcp import AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete
from katcp.resource_client import KATCPClientResource
from katcp.ioloop_manager import with_relative_timeout
from reynard.utils import pack_dict, unpack_dict
from reynard.servers.ubi_server import UniversalBackendInterface
import redis

log = logging.getLogger("reynard.ubi_server")

class BLBackendInterface(UniversalBackendInterface):
    """Breakthrough Listen's KATCP Server Backend Interface

    Attributes:
        attr1 (str): Description of `attr1`.
        attr2 (:obj:`int`, optional): Description of `attr2`.


    """

    VERSION_INFO = ("breakthrough-katcp-interface", 0, 1)
    BUILD_INFO = ("breakthrough-katcp-implementation", 0, 1, "rc?")
    DEVICE_STATUSES = ["ok", "fail", "degraded"]

    class REDIS_CHANNELS:
        """The redis channels that I publish to"""
        alerts = "alerts"


    def __init__(self, server_host, server_port):
        self.port = server_port
        self.redis_server = redis.StrictRedis()
        super(BLBackendInterface, self).__init__(
            server_host, server_port)

    def start(self):
        """Start the server

        Based on the passed configuration object this is
        where the clients for suboridnates nodes will be
        set up.
        """
        super(BLBackendInterface, self).start()
        print (R"""
                      ,'''''-._
                     ;  ,.  <> `-._
                     ;  \'   _,--'"
                    ;      (
                    ; ,   ` \
                    ;, ,     \
                   ;    |    |
                   ; |, |    |\       MeerKAT BL Backend Interface:
                  ;  |  |    | \      Version: {}
                  |.-\ ,\    |\ :     Port: {}
                  |.| `. `-. | ||
                  :.|   `-. \ ';;
                   .- ,   \;;|
                   ;   ,  |  ,\
                   ; ,    ;    \      https://github.com/ejmichaud/meerkat-backend-interface
                  ;    , /`.  , )
               __,;,   ,'   \  ,|
         _,--''__,|   /      \  :
       ,'_,-''    | ,/        | :
      / /         | ;         ; |
     | |      __,-| |--..__,--| |---.--....___
___,-| |----''    / |         `._`-.          `----
      \ \        `'''             '''      --
       `.`.                 --'
         `.`-._        _,             ,-     __,-
            `-.`.
   --'         `;
        """.format("{}.{}".format(self.VERSION_INFO[1], self.VERSION_INFO[2]), self.port))

    def _write_to_redis(self, key, value):
        """Creates a key-value pair self.redis_server's redis-server.

        Args:
            key (str): the key of the key-value pair
            value (str): the value of the key-value pair
        
        Returns:
            None... but logs either an 'info' or 'error' message
        
        Examples:
            >>> server = BLBackendInterface('localhost', 5000)
            >>> server._write_to_redis("aliens:found", "yes")
        """
        try:
            self.redis_server.set(key, value)
            log.info("Created redis key/value: {} --> {}".format(key, value))
        except:
            log.error("Failed to create redis key/value pair")

    def _publish_to_redis(self, channel, message):
        """Publishes a message to a channel in self.redis_server's redis-server.

        Args:
            channel (str): the name of the channel to publish to
            message (str): the message to be published
        
        Returns:
            None... but logs either an 'info' or 'error' message
        
        Examples:
            >>> server = BLBackendInterface('localhost', 5000)
            >>> server._publish_to_redis("alerts", "Found aliens!!!")
        """
        try:
            self.redis_server.publish(channel, message)
            log.info("Published to {} --> {}".format(channel, message))
        except:
            log.error("Failed to publish to {}".format(channel))

    @request(Str(), Str(), Int(), Str(), Str())
    @return_reply(Str())
    def request_configure(self, req, product_id, antennas_csv, \
                n_channels, streams_json, proxy_name):
        """Receive metadata for upcoming observation.

        In order to allow BLUSE to make an estimate of its ability 
        to process a particular data product, this command should 
        be used to configure a BLUSE instance when a new subarray is activated.
        
        TODO:
            If using katportalclient to get information from CAM, 
            then reconnect and re-subscribe to all sensors of interest at this time.

        Args:
            product_id (str): This is a name for the data product, 
                    which is a useful tag to include in the data, 
                    but should not be analysed further.  
                    For example "array_1_bc856M4k". This value will 
                    be unique across all subarrays. However, it is 
                    not a globally unique identifier for the lifetime 
                    of the telescope.  The exact same value may be provided 
                    at a later time when the same subarray is activated again.
            
            antennas_csv (str): A comma separated list of physical antenna names 
                    used in particular sub-array to which the data products belongs.
            
            n_channels (int): The integer number of frequency channels provided by the CBF.
            
            streams_json (str) is a JSON struct containing config keys and 
                    values describing the streams.  For example: 
                    {'stream_type1': {
                    'stream_name1': 'stream_address1',
                    'stream_name2': 'stream_address2',
                    ...}, 
                 'stream_type2': {
                    'stream_name1': 'stream_address1',
                    'stream_name2': 'stream_address2',
                    ...},
                    ...}
                The steam type keys indicate the source of the data and the type, e.g. cam.http.
                stream_address will be a URI.  For SPEAD streams, the format will be 
                spead://<ip>[+<count>]:<port>, representing SPEAD stream multicast groups. 
                When a single logical stream requires too much bandwidth to accommodate 
                as a single multicast group, the count parameter indicates the number of 
                additional consecutively numbered multicast group ip addresses, and 
                sharing the same UDP port number.
                stream_name is the name used to identify the stream in CAM.
                A Python example is shown below, for five streams:
                One CAM stream, with type cam.http.  The camdata stream provides the 
                connection string for katportalclient (for the subarray that this 
                BLUSE instance is being configured on).
                One F-engine stream, with type:  cbf.antenna_channelised_voltage.
                One X-engine stream, with type:  cbf.baseline_correlation_products.
                Two beam streams, with type: cbf.tied_array_channelised_voltage.  
                The stream names ending in x are horizontally polarised, and those 
                ending in y are vertically polarised.

        proxy_name (str): The CAM name for the instance of the BLUSE data 
        proxy that is being configured.  For example, "BLUSE_3".  This 
        can be used to query sensors on the correct proxy.  Note that for 
        BLUSE there will only be a single instance of the proxy in a subarray.

        Returns:
            None... but replies with "ok" and logs either info or error

        Examples:
            > ?configure array_1_bc856M4k a1,a2,a3,a4 128000 {'stream_type1':{'stream_name1':'stream_address1','stream_name2':'stream_address2'},'stream_type2':{'stream_name1':'stream_address1','stream_name2':'stream_address2'}} BLUSE_3
        """
        try:
            antennas_list = antennas_csv.split(",")
            data_dictionary = {
                "product_id": product_id,
                "antennas_list": antennas_list,
                "n_channels": n_channels,
                "streams_json": streams_json, # try repr(unpack_dict(streams_json))
                "proxy_name": proxy_name
            }
            json_data_dictionary = json.dumps(data_dictionary)
            self._write_to_redis("current:observation:metadata", json_data_dictionary)
            self._publish_to_redis(self.REDIS_CHANNELS.alerts, json_data_dictionary)
            return ("ok", "")
        except Exception as e:
            return ("fail", e)

    @request(Str())
    @return_reply(Str())
    def request_capture_init(self, req, product_id):
        """Signals that an observation will start soon
        
            Publishes a message to the 'alerts' channel of the form:
                capture-init:product_id
            The product_id should match what what was sent in the ?configure request

            This alert should notify all backend processes (such as beamformer)
            to get ready for data
        """
        msg = "capture-init:{}".format(product_id)
        self._publish_to_redis(self.REDIS_CHANNELS.alerts, msg)
        return ("ok", "")

    @request(Str())
    @return_reply(Str())
    def request_capture_start(self, req, product_id):
        """Signals that an observation is starting now
        
            Publishes a message to the 'alerts' channel of the form:
                capture-start:product_id
            The product_id should match what what was sent in the ?configure request

            This alert should notify all backend processes (such as beamformer)
            that they need to be collecting data now
        """
        msg = "capture-start:{}".format(product_id)
        self._publish_to_redis(self.REDIS_CHANNELS.alerts, msg)
        return ("ok", "")

    @request(Str())
    @return_reply(Str())
    def request_capture_done(self, req, product_id):
        """Signals that an observation has finished
        
            Publishes a message to the 'alerts' channel of the form:
                capture-done:product_id
            The product_id should match what what was sent in the ?configure request

            This alert should notify all backend processes (such as beamformer)
            that their data streams are ending
        """
        msg = "capture-done:{}".format(product_id)
        self._publish_to_redis(self.REDIS_CHANNELS.alerts, msg)
        return ("ok", "")

    @request(Str())
    @return_reply(Str())
    def request_deconfigure(self, req, product_id):
        """Signals that the current data product is done.
        
            Deconfigure the BLUSE instance that was created by the call 
            to ?configure with the corresponding product_id. Note:  CAM is 
            expected to have sent a ?capture-done request before deconfiguring, 
            in order to ensure that all data has been written. If BLUSE uses an 
            instance of katportalclient to get information from CAM for this 
            BLUSE instance, then it should disconnect at this time. 

            Publishes a message to the 'alerts' channel of the form:
                deconfigure:product_id
            The product_id should match what what was sent in the ?configure request

            This alert should notify all backend processes (such as beamformer)
            that their data streams are ending
        """
        msg = "deconfigure:{}".format(product_id)
        self._publish_to_redis(self.REDIS_CHANNELS.alerts, msg)
        return ("ok", "")
    
    @request(Str())
    @return_reply(Str())
    def request_save(self, req, msg):
        """Saves msg to redis channel 'alerts'
        """
        self._publish_to_redis(self.REDIS_CHANNELS.alerts, msg)
        return ("ok", "published: {}".format(msg))

    @request()
    @return_reply(Str())
    def request_find_alien(self, req):
        """Finds an alien.
        """
        return ("ok", R"""
.     .       .  .   . .   .   . .    +  .
  .     .  :     .    .. :. .___---------___.
       .  .   .    .  :.:. _".^ .^ ^.  '.. :"-_. .
    .  :       .  .  .:../:            . .^  :.:\.
        .   . :: +. :.:/: .   .    .        . . .:\
 .  :    .     . _ :::/:               .  ^ .  . .:\
  .. . .   . - : :.:./.                        .  .:\
  .      .     . :..|:                    .  .  ^. .:|
    .       . : : ..||        .                . . !:|
  .     . . . ::. ::\(                           . :)/
 .   .     : . : .:.|. ######              .#######::|
  :.. .  :-  : .:  ::|.#######           ..########:|
 .  .  .  ..  .  .. :\ ########          :######## :/
  .        .+ :: : -.:\ ########       . ########.:/
    .  .+   . . . . :.:\. #######       #######..:/
      :: . . . . ::.:..:.\           .   .   ..:/
   .   .   .  .. :  -::::.\.       | |     . .:/
      .  :  .  .  .-:.":.::.\             ..:/
 .      -.   . . . .: .:::.:.\.           .:/
.   .   .  :      : ....::_:..:\   ___.  :/
   .   .  .   .:. .. .  .: :.:.:\       :/
     +   .   .   : . ::. :.:. .:.|\  .:/|
     .         +   .  .  ...:: ..|  --.:|
.      . . .   .  .  . ... :..:.."(  ..)"
 .   .       .      :  .   .: ::/  .  .::\            
        """)


# class BLBackendInterface(AsyncDeviceServer):


#     def __init__(self, server_host, server_port):
#         self._nodes = {}
#         self.port = server_port
#         super(BLBackendInterface, self).__init__(
#             server_host, server_port)

#     def setup_sensors(self):
#         """add sensors"""
#         pass

    

#     def _add_node(self, name, ip, port):
#         """Add a named node."""
#         log.debug("Adding node '{0}' ({1}:{2})".format(name, ip, port))
#         if name in self._nodes.keys():
#             raise KeyError(
#                 "Node already added with name '{name}'".format(
#                     name=name))
#         client = KATCPClientResource(dict(
#             name=name,
#             address=(ip, port),
#             controlled=True))
#         client.start()
#         self._nodes[name] = client

#     def _remove_node(self, name):
#         """Remove a client by name."""
#         log.debug("Removing node '{0}'".format(name))
#         if name not in self._nodes.keys():
#             raise KeyError(
#                 "No node exists with name '{name}'".format(
#                     name=name))
#         self._nodes[name].stop()
#         del self._nodes[name]

#     # def request_weather(self, req):
#     #     f = Future()
#     #     @gen.coroutine
#     #     def _halt():
#     #         from weather import Weather, Unit
#     #         location = Weather(unit=Unit.FAHRENHEIT).lookup_by_location('Berkeley, CA')
#     #         req.reply(location.condition.temp)
#     #         yield gen.moment
#     #         self.stop(timeout=None)
#     #         raise AsyncReply
#     #     self.ioloop.add_callback(lambda: chain_future(_halt(), f))
#     #     return f

#     def request_weather(self, req, msg):
#         """ Docstring. Are you happy now?

#         """
#         if not msg.arguments:
#             location = "Berkeley, CA"
#         else:
#             location = ' '.join(msg.arguments)
#         from weather import Weather, Unit
#         weather_local = Weather(unit=Unit.FAHRENHEIT).lookup_by_location(location)
#         #name = msg.arguments[0]
#         # if name in self._request_handlers:
#         #     method = self._request_handlers[name]
#         #     doc = method.__doc__.strip()
#         #     req.inform(name, doc)
#         return req.make_reply(" :::  Weather in {} --> {} *F".format(location, weather_local.condition.temp))
#         #return req.make_reply("fail", "Unknown request method.")

#         # for name, method in sorted(self._request_handlers.items()):
#         #         doc = method.__doc__
#         #         req.inform(name, doc)
#         #     num_methods = len(self._request_handlers)
#         #     return req.make_reply("ok", str(num_methods))

#     @request(Str(), Str())
#     @return_reply(Str(), Str())
#     def request_configure(self, req, config, sensors):
#         """config"""
#         @coroutine
#         def configure(config):
#             futures = {}
#             node_count = len(config["nodes"])
#             configured = 0
#             for node in config["nodes"]:
#                 host, port = node["host"], node["port"]
#                 ip = socket.gethostbyname(host)
#                 log.debug("Searching for node at {0}:{1}".format(ip, port))
#                 for name, client in self._nodes.items():
#                     log.debug("Testing client {0} at {1}".format(name,client.address))
#                     if client.address == (ip, port) and client.is_connected():
#                         log.debug(
#                             "Found node at {0}:{1} named {2}".format(
#                                 ip, port, name))
#                         log.debug(
#                             "Pipeline config for node: {0}".format(
#                                 node["pipelines"]))
#                         req.inform(
#                             "Configuring node '{0}' ({1}:{2})".format(
#                                 name, ip, port))
#                         futures[name] = client.req.configure(
#                             pack_dict(node["pipelines"]),
#                             sensors, timeout=30)
#                         break
#                 else:
#                     msg = "No node found at {0}:{1}".format(ip, port)
#                     req.inform(msg)
#                     log.warning(msg)

#             for name, future in futures.items():
#                 response = yield future
#                 if not response.reply.reply_ok():
#                     req.inform(
#                         "Configuration failure from node '{0}': {1}".format(
#                             name, str(
#                                 response.messages)))
#                 else:
#                     configured += 1
#             if configured >= 1:
#                 req.reply(
#                     "ok", "Configured {0} of {1} nodes".format(
#                         configured, node_count))
#             else:
#                 req.reply("fail", "No nodes configured")
#         self.ioloop.add_callback(lambda: configure(unpack_dict(config)))
#         raise AsyncReply

#     @coroutine
#     def _all_nodes_request(self, req, cmd, *args, **kwargs):
#         log.debug("Sending '{0}' request to all nodes".format(cmd))
#         futures = {}
#         for name, client in self._nodes.items():
#             if client.is_connected():
#                 futures[name] = client.req[cmd](*args, **kwargs)
#         for name, future in futures.items():
#             response = yield future
#             if not response.reply.reply_ok():
#                 msg = "Failure on '{0}' request to node '{1}': {2}".format(
#                     cmd, name, str(response.messages))
#                 log.error(msg)
#                 req.reply("fail", msg)
#                 return
#         msg = "{0} request complete".format(cmd)
#         log.debug(msg)
#         req.reply("ok", msg)

#     @request(Str())
#     @return_reply(Str())
#     def request_start(self, req, sensors):
#         """start"""
#         self.ioloop.add_callback(
#             lambda: self._all_nodes_request(
#                 req, "start", sensors, timeout=20.0))
#         raise AsyncReply

#     @request()
#     @return_reply(Str())
#     def request_stop(self, req):
#         """stop"""
#         self.ioloop.add_callback(
#             lambda: self._all_nodes_request(
#                 req, "stop", timeout=20.0))
#         raise AsyncReply

#     @request()
#     @return_reply(Str())
#     def request_deconfigure(self, req):
#         """deconfig"""
#         self.ioloop.add_callback(
#             lambda: self._all_nodes_request(
#                 req, "deconfigure", timeout=20.0))
#         raise AsyncReply

#     @request(Str(), Str(), Int())
#     @return_reply(Str())
#     def request_node_add(self, req, name, ip, port):
#         """Add a new node."""
#         try:
#             self._add_node(name, ip, port)
#         except KeyError as e:
#             return ("fail", str(e))
#         return ("ok", "added node")

#     @request(Str())
#     @return_reply(Str())
#     def request_node_remove(self, req, name):
#         """Add a new node."""
#         try:
#             self._remove_node(name)
#         except KeyError as e:
#             return ("fail", str(e))
#         return ("ok", "removed node")

#     @request()
#     @return_reply(Str())
#     def request_node_list(self, req):
#         """List all connected nodes"""
#         msg = [""]
#         for ii, (name, node) in enumerate(self._nodes.items()):
#             up = "[online]" if node.is_connected() else "[offline]"
#             addr = "{0}:{1}".format(*node.address)
#             msg.append("{node.name: <12} {addr} {up}".format(
#                 node=node, addr=addr, up=up))
#         req.inform("\n\_\_\_\_".join(msg))
#         return ("ok", "{count} nodes found".format(count=len(self._nodes)))

#     @request()
#     @return_reply(Str())
#     def request_status(self, req):
#         """Return status for UBI backend"""
#         status = {}
#         @coroutine
#         def status_query():
#             futures = {}
#             for name, client in self._nodes.items():
#                 if not client.is_connected():
#                     status[name] = {"status":"offline"}
#                     continue
#                 else:
#                     status[name] = {"status":"online"}
#                     futures[name] = client.req.status()
#             for name, future in futures.items():
#                 response = yield future
#                 status[name].update(unpack_dict(response.reply.arguments[1]))
#             req.reply("ok",pack_dict(status))
#         self.ioloop.add_callback(status_query)
#         raise AsyncReply

#     @request()
#     @return_reply(Discrete(DEVICE_STATUSES))
#     def request_device_status(self, req):
#         """Return status of the instrument.

#         Notes: Status is based on aggregate information
#                from all subordinate nodes.

#         Currently this is a dummy function to test chaining
#         async calls.
#         """
#         @coroutine
#         def status_handler():
#             futures = {}
#             for name, client in self._nodes.items():
#                 if client.is_connected():
#                     future = client.req.device_status()
#                     futures[name] = future
#             statuses = {}
#             for name, future in futures.items():
#                 with_relative_timeout(2, future)
#                 status = yield future
#                 if not status:
#                     req.inform(
#                         "Warning {name} status request failed: {msg}".format(
#                             name=name, msg=str(status)))
#                 reply = status.reply
#                 status_message = reply.arguments[1]
#                 req.inform("Client {name} state: {msg}".format(
#                     name=name, msg=status_message))
#                 statuses[name] = reply.arguments[1] == "ok"
#             passes = [success for name, success in statuses.items()]
#             if all(passes):
#                 req.reply("ok", "ok")
#             else:
#                 # some policy for degradation needs to be determined based on
#                 # overall instrument capability. Maybe fraction of beams x
#                 # bandwidth?
#                 fail_count = len(passes) - sum(passes)
#                 if fail_count > 1:
#                     req.reply("ok", "fail")
#                 else:
#                     req.reply("ok", "degraded")

#         self.ioloop.add_callback(status_handler)
#         raise AsyncReply
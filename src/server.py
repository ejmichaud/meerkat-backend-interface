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
import time
from tornado.gen import coroutine
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete
from katcp.resource_client import KATCPClientResource
from katcp.ioloop_manager import with_relative_timeout
from reynard.utils import pack_dict, unpack_dict
from reynard.servers.ubi_server import UniversalBackendInterface
import redis

log = logging.getLogger("reynard.ubi_server")

class BLBackendInterface(AsyncDeviceServer):
    """Breakthrough Listen's KATCP Server Backend Interface

    Attributes:
        attr1 (str): Description of `attr1`.
        attr2 (:obj:`int`, optional): Description of `attr2`.


    """

    VERSION_INFO = ("BLUSE-katcp-interface", 0, 1)
    BUILD_INFO = ("BLUSE-katcp-implementation", 0, 1, "rc?")
    DEVICE_STATUSES = ["ok", "fail", "degraded"]

    class REDIS_CHANNELS:
        """The redis channels that may be published to"""
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

    def _write_pair_redis(self, key, value):
        """Creates a key-value pair self.redis_server's redis-server.

        Args:
            key (str): the key of the key-value pair
            value (str): the value of the key-value pair
        
        Returns:
            None... but logs either an 'debug' or 'error' message
        
        Examples:
            >>> server = BLBackendInterface('localhost', 5000)
            >>> server._write_to_redis("aliens:found", "yes")
        """
        try:
            self.redis_server.set(key, value)
            log.debug("Created redis key/value: {} --> {}".format(key, value))
        except:
            log.error("Failed to create redis key/value pair")

    def _write_list_redis(self, key, values):
        """Creates a new list and rpushes values to it

            If a list already exists at the given key, then
            delete it and rpush values to a new empty list
            
            Args:
                key (str): key identifying the list
                values (list): list of values to rpush to redis list

        """
        if self.redis_server.exists(key):
            self.redis_server.delete(key)
        try:
            self.redis_server.rpush(key, *values)
            log.debug("Pushed to list: {} --> {}".format(key, values))
        except:
            log.error("Failed to rpush to {}".format(channel))

    def _publish_to_redis(self, channel, message):
        """Publishes a message to a channel in self.redis_server's redis-server.

        Args:
            channel (str): the name of the channel to publish to
            message (str): the message to be published
        
        Returns:
            None... but logs either an 'debug' or 'error' message
        
        Examples:
            >>> server = BLBackendInterface('localhost', 5000)
            >>> server._publish_to_redis("alerts", "Found aliens!!!")
        """
        try:
            self.redis_server.publish(channel, message)
            log.debug("Published to {} --> {}".format(channel, message))
        except:
            log.error("Failed to publish to {}".format(channel))

    @request(Str(), Str(), Int(), Str(), Str())
    @return_reply()
    def request_configure(self, req, product_id, antennas_csv, \
                n_channels, streams_json, proxy_name):
        """Receive metadata for upcoming observation.

        In order to allow BLUSE to make an estimate of its ability 
        to process a particular data product, this command should 
        be used to configure a BLUSE instance when a new subarray is activated.
        
        TODO:
            - If using katportalclient to get information from CAM, 
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
            
        Writes:
            - subbarry1_abc65555:timestamp" -> "1534657577373.23423"  :: Redis String
            - subarray1_abc65555:antennas" -> [1,2,3,4] :: Redis List
            - subarray1_abc65555:n_channels" -> "4096" :: Redis String
            - subarray1_abc65555:proxy_name "-> "BLUSE_whatever" :: Redis String
            - subarray1_abc65555:streams" -> {....} :: Redis Hash !!!CURRENTLY A STRING!!!
            - current:obs:metadata -> "subbary1_abc65555"

        Publishes:
            redis-channel: 'alerts' <-- "configure"
        
        Examples:
            > ?configure array_1_bc856M4k a1,a2,a3,a4 128000 {"stream_type1":{"stream_name1":"stream_address1","stream_name2":"stream_address2"},"stream_type2":{"stream_name1":"stream_address1","stream_name2":"stream_address2"}} BLUSE_3
        """
        try:
            antennas_list = antennas_csv.split(",")
            self._write_pair_redis("{}:timestamp".format(product_id), time.time())
            self._write_list_redis("{}:antennas".format(product_id), antennas_list)
            self._write_pair_redis("{}:n_channels".format(product_id), n_channels)
            self._write_pair_redis("{}:proxy_name".format(product_id), proxy_name)
            self._write_pair_redis("{}:streams".format(product_id), repr(unpack_dict(streams_json)))
            self._write_pair_redis("current:obs:metadata", product_id)
            self._write_pair_redis(product_id, repr((streams_json)))
            self._publish_to_redis(self.REDIS_CHANNELS.alerts, "configure")
            return ("ok",)
        except Exception as e:
            return ("fail", e)

    @request(Str())
    @return_reply()
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
        return ("ok",)

    @request(Str())
    @return_reply()
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
        return ("ok",)

    @request(Str())
    @return_reply()
    def request_capture_stop(self, req, product_id):
        """Signals that an observation is has stopped
        
            Publishes a message to the 'alerts' channel of the form:
                capture-stop:product_id
            The product_id should match what what was sent in the ?configure request

            This alert should notify all backend processes (such as beamformer)
            that they should stop collecting data now
        """
        msg = "capture-stop:{}".format(product_id)
        self._publish_to_redis(self.REDIS_CHANNELS.alerts, msg)
        return ("ok",)

    @request(Str())
    @return_reply()
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
        return ("ok",)

    @request(Str())
    @return_reply()
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
        return ("ok",)
    
    def setup_sensors(self):
        """
        @brief    Set up monitoring sensors.

        @note     The following sensors are made available on top of defaul sensors
                  implemented in AsynDeviceServer and its base classes.

                  device-status:      Reports the health status of the FBFUSE and associated devices:
                                      Among other things report HW failure, SW failure and observation failure.
        """
        self._device_status = Sensor.discrete(
            "device-status",
            description="Health status of BLUSE",
            params=self.DEVICE_STATUSES,
            default="ok",
            initial_status=Sensor.NOMINAL)
        self.add_sensor(self._device_status)

        self._local_time_synced = Sensor.boolean(
            "local-time-synced",
            description="Indicates FBF is NTP syncronised.",
            default=True,
            initial_status=Sensor.NOMINAL)
        self.add_sensor(self._local_time_synced)

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



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

import sys
import logging
import socket
import json
import time
from tornado.gen import coroutine
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete
from reynard.utils import pack_dict, unpack_dict

import redis
from redis_tools import REDIS_CHANNELS, write_pair_redis, write_list_redis, publish_to_redis
from slack_tools import notify_slack

from concurrent.futures import Future
from tornado import gen

log = logging.getLogger("BLUSE.interface")

class BLBackendInterface(AsyncDeviceServer):
    """Breakthrough Listen's KATCP Server Backend Interface

    This server responds to requests sent from CAM, most notably:
        @ configue
        @ capture-init
        @ capture-start
        @ capture-stop
        @ capture-done
        @ deconfigure

    But because it inherits from AsyncDeviceServer, also responds to:
        * halt
        * help
        * log-level
        * restart [#restartf1]_
        * client-list
        * sensor-list
        * sensor-sampling
        * sensor-value
        * watchdog
        * version-list (only standard in KATCP v5 or later)
        * request-timeout-hint (pre-standard only if protocol flags indicates
                              timeout hints, supported for KATCP v5.1 or later)
        * sensor-sampling-clear (non-standard)

    TODO:
        Override halt request to send message to slack, publish to redis,
        publish to syslog, and stop the whole server process with sys.exit(0)
    """

    VERSION_INFO = ("BLUSE-katcp-interface", 0, 1)
    BUILD_INFO = ("BLUSE-katcp-implementation", 0, 1, "rc?")
    DEVICE_STATUSES = ["ok", "fail", "degraded"]


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
            write_pair_redis(self.redis_server, "{}:timestamp".format(product_id), time.time())
            write_list_redis(self.redis_server, "{}:antennas".format(product_id), antennas_list)
            write_pair_redis(self.redis_server, "{}:n_channels".format(product_id), n_channels)
            write_pair_redis(self.redis_server, "{}:proxy_name".format(product_id), proxy_name)
            write_pair_redis(self.redis_server, "{}:streams".format(product_id), repr(unpack_dict(streams_json)))
            write_pair_redis(self.redis_server, "current:obs:metadata", product_id)
            publish_to_redis(self.redis_server, REDIS_CHANNELS.alerts, "configure")
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
        publish_to_redis(self.redis_server, REDIS_CHANNELS.alerts, msg)
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
        publish_to_redis(self.redis_server, REDIS_CHANNELS.alerts, msg)
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
        publish_to_redis(self.redis_server, REDIS_CHANNELS.alerts, msg)
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
        publish_to_redis(self.redis_server, REDIS_CHANNELS.alerts, msg)
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
        publish_to_redis(self.redis_server, REDIS_CHANNELS.alerts, msg)
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
            description="Indicates BLUSE is NTP syncronised.",
            default=True,
            initial_status=Sensor.NOMINAL)
        self.add_sensor(self._local_time_synced)

    @request(Str())
    @return_reply(Str())
    def request_save(self, req, msg):
        """Saves msg to redis channel 'alerts'
        """
        publish_to_redis(self.redis_server, REDIS_CHANNELS.alerts, msg)
        return ("ok", "published: {}".format(msg))

    def request_halt(self, req, msg):
        """Halt the device server.
        Returns
        -------
        success : {'ok', 'fail'}
            Whether scheduling the halt succeeded.
        Examples
        --------
        ::
            ?halt
            !halt ok
        """
        f = Future()
        @gen.coroutine
        def _halt():
            req.reply("ok")
            yield gen.moment
            self.stop(timeout=None)
            raise AsyncReply

        log.critical("HALTING SERVER!!!")
        notify_slack("TEST: KATCP server on blh1 (Cape Town) has halted. Might want to check that!")
        self.ioloop.add_callback(lambda: chain_future(_halt(), f))
        sys.exit(0)

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



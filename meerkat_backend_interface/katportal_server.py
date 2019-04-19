from __future__ import print_function

import tornado.gen
import uuid
from katportalclient import KATPortalClient
from katportalclient.client import SensorNotFoundError
import redis
from functools import partial

from .redis_tools import (
    REDIS_CHANNELS,
    write_pair_redis,
    write_list_redis,
    )
from .logger import log as logger


class BLKATPortalClient(object):
    """Our client server to the Katportal

    Examples:
        >>> client = BLKATPortalClient()
        >>> client.start()

    Yes, it's that simple. (but katportal_start does something a little fancier!)

    Once initialized, the client creates a Tornado ioloop and
    a connection to the local Redis server.

    When start() is called, a loop starts that subscribes to the 'alerts'
    channel of the Redis server. Depending on the message received, various
    processes are run (asynchronously?). These include:
        1. Creating a new KATPortalClient object specific to the
            product id we just received in a ?configure request
        2. Querying for schedule block information when ?capture-init is
            received and publishing this to Redis
        3. Querying for target information when ?capture-start is
            received and publishing this to Redis
        4. Deleting the corresponding KATPortalClient object when
            a ?deconfigure request is sent.

    TODO:
        1. Support thread-safe stopping of ioloop
    """

    VERSION = 1.0

    def __init__(self):
        """Our client server to the Katportal"""
        self.redis_server = redis.StrictRedis()
        self.p = self.redis_server.pubsub(ignore_subscribe_messages=True)
        self.io_loop = io_loop = tornado.ioloop.IOLoop.current()
        self.subarray_katportals = dict()  # indexed by product id's
        self.ant_sensors = ['marked_faulty', 'data_suspect']  # sensors required from each antenna
        self.async_sensor_list = []  # will be populated with sensors for subscription

    def MSG_TO_FUNCTION(self, msg_type):
        MSG_TO_FUNCTION_DICT = {
            'configure'    : self._configure,
            'capture-init' : self._capture_init,
            'capture-start': self._capture_start,
            'capture-stop' : self._capture_stop,
            'capture-done' : self._capture_done,
            'deconfigure'  : self._deconfigure
        }
        return MSG_TO_FUNCTION_DICT.get(msg_type, self._other)

    def start(self):
        self.p.subscribe(REDIS_CHANNELS.alerts)
        self._print_start_image()
        for message in self.p.listen():
            msg_parts = message['data'].split(':')
            if len(msg_parts) != 2:
                logger.info("Not processing this message --> {}".format(message))
                continue
            msg_type = msg_parts[0]
            product_id = msg_parts[1]
            self.MSG_TO_FUNCTION(msg_type)(product_id)

    def on_update_callback_fn(self, product_id, msg):
        """Handler for messages published over sensor websockets.
        The received sensor values are stored in the redis database.

        Args:
            product_id (str): the product id given in the ?configure request
            msg (dict): a dictionary containing the updated sensor information

        Returns:
            None
        """
        for key, value in msg.items():
            if key == 'msg_data':
                sensor_name = msg['msg_data']['name']
                sensor_value = msg['msg_data']['value']
                if sensor_name in self.async_sensor_list:
                    key = "{}:{}".format(product_id, sensor_name)
                    write_pair_redis(self.redis_server, key, repr(sensor_value))
                    print('Sensor value stored: {} = {}'.format(sensor_name, sensor_value))
                else:
                    print('Unlisted sensor; value discarded')

    def gen_ant_sensor_list(self, product_id, ant_sensors):
        """Automatically builds a list of sensor names for each antenna.

        Args:
            product_id (str): the product id given in the ?configure request
            ant_sensors (list): the sensors to be queried for each antenna

        Returns:
            ant_sensor_list (list): the full sensor names associated with each antenna
        """
        ant_sensor_list = []
        # Add sensors specific to antenna components for each antenna:
        ant_key = '{}:antennas'.format(product_id)
        ant_list = self.redis_server.lrange(ant_key, 0, self.redis_server.llen(ant_key))  # list of antennas
        for ant in ant_list:
            for sensor in ant_sensors:
                ant_sensor_list.append(ant + '_' + sensor)
        return ant_sensor_list

    @tornado.gen.coroutine
    def subscribe_sensors(self, product_id):
        """Subscribes to each sensor listed for asynchronous updates.

        Args:
            product_id (str): the product id given in the ?configure request

        Returns:
            None
        """
        self.async_sensor_list = self.async_sensor_list + self.gen_ant_sensor_list(product_id, self.ant_sensors)
        yield self.subarray_katportals[product_id].connect()
        namespace = 'namespace_' + str(uuid.uuid4())
        result = yield self.subarray_katportals[product_id].subscribe(namespace)
        for sensor in self.async_sensor_list:
            result = yield self.subarray_katportals[product_id].set_sampling_strategies(namespace, sensor, 'event')
            print('Subscribed to sensor: {}'.format(sensor))

    def _configure(self, product_id):
        """Executes when configure request is processed

        Args:
            product_id (str): the product id given in the ?configure request

        Returns:
            None
        """
        cam_url = self.redis_server.get("{}:{}".format(product_id, 'cam:url'))
        client = KATPortalClient(cam_url, on_update_callback=partial(self.on_update_callback_fn, product_id), logger=logger)
        #client = KATPortalClient(cam_url, on_update_callback=lambda x: self.on_update_callback_fn(product_id), logger=logger)
        self.subarray_katportals[product_id] = client
        logger.info("Created katportalclient object for : {}".format(product_id))
        sensors_to_query = []  # TODO: add sensors to query on ?configure
        sensors_and_values = self.io_loop.run_sync(
            lambda: self._get_sensor_values(product_id, sensors_to_query))
        for sensor_name, value in sensors_and_values.items():
            key = "{}:{}".format(product_id, sensor_name)
            write_pair_redis(self.redis_server, key, repr(value))

    def _capture_init(self, product_id):
        """Responds to capture-init request by getting schedule blocks

        Args:
            product_id (str): the product id given in the ?configure request

        Returns:
            None
        """
        schedule_blocks = self.io_loop.run_sync(lambda: self._get_future_targets(product_id))
        key = "{}:schedule_blocks".format(product_id)
        write_list_redis(self.redis_server, key, repr(schedule_blocks))  # overrides previous list
        # Start io_loop to listen to sensors whose values should be registered
        # immediately when they change.
        self.io_loop.add_callback(lambda: self.subscribe_sensors(product_id))
        self.io_loop.start()
        # Once off sensor values
        sensors_to_query = []  # TODO: add sensors to query on ?capture_init
        sensors_and_values = self.io_loop.run_sync(
            lambda: self._get_sensor_values(product_id, sensors_to_query))
        for sensor_name, value in sensors_and_values.items():
            key = "{}:{}".format(product_id, sensor_name)
            write_pair_redis(self.redis_server, key, repr(value))

    def _capture_start(self, product_id):
        """Responds to capture-start request

        Args:
            product_id (str): the product id given in the ?configure request

        Returns:
            None, but does many things!
        """
        # TODO: get more information?
        sensors_to_query = ['target', 'pos_request_base_ra', 'pos_request_base_dec', 'weight']
        sensors_and_values = self.io_loop.run_sync(
            lambda: self._get_sensor_values(product_id, sensors_to_query))
        for sensor_name, value in sensors_and_values.items():
            key = "{}:{}".format(product_id, sensor_name)
            write_pair_redis(self.redis_server, key, repr(value))

    def _capture_stop(self, product_id):
        """Responds to capture-stop request

        Args:
            product_id (str): the product id given in the ?configure request

        Returns:
            None, but does many things!
        """
        #msg_parts = message['data'].split(':')
        #product_id = msg_parts[1] # the element after the capture-stop identifier
        #client = self.subarray_katportals[product_id]
        # TODO: get more information?
        print('Capture stopped')

    def _capture_done(self, product_id):
        """Responds to capture-done request

        Args:
            product_id (str): the product id given in the ?configure request

        Returns:
            None, but does many things!
        """
        # Stop io_loop for async_sensor_list
        self.io_loop.stop()
        # Once-off sensors to query on ?capture_done
        sensors_to_query = []  # TODO: add sensors to query on ?capture_done
        sensors_and_values = self.io_loop.run_sync(
            lambda: self._get_sensor_values(product_id, sensors_to_query))
        for sensor_name, value in sensors_and_values.items():
            key = "{}:{}".format(product_id, sensor_name)
            write_pair_redis(self.redis_server, key, repr(value))

    def _deconfigure(self, product_id):
        """Responds to deconfigure request

        Args:
            product_id (str): the product id given in the ?configure request

        Returns:
            None
        """
        sensors_to_query = []  # TODO: add sensors to query on ?deconfigure
        sensors_and_values = self.io_loop.run_sync(
            lambda: self._get_sensor_values(product_id, sensors_to_query))
        for sensor_name, value in sensors_and_values.items():
            key = "{}:{}".format(product_id, sensor_name)
            write_pair_redis(self.redis_server, key, repr(value))
        if product_id not in self.subarray_katportals:
            logger.warning("Failed to deconfigure a non-existent product_id: {}".format(product_id))
        else:
            self.subarray_katportals.pop(product_id)
            logger.info("Deleted KATPortalClient instance for product_id: {}".format(product_id))

    def _other(self, product_id):
        """This is called when an unrecognized request is sent

        Args:
            product_id (str): the product id given in the ?configure request

        Returns:
            None
        """
        logger.warning("Unrecognized alert : {}".format(message['data']))

    @tornado.gen.coroutine
    def _get_future_targets(self, product_id):
        """Gets the schedule blocks of the product_id's subarray

        Args:
            product_id (str): the product id of a currently activated subarray

        Returns:
            List of dictionaries containing schedule block information

        Examples:
            >>> self.io_loop.run_sync(lambda: self._get_future_targets(product_id))
        """
        client = self.subarray_katportals[product_id]
        sb_ids = yield client.schedule_blocks_assigned()
        blocks = []
        for sb_id in sb_ids:
            # Should this be 'client' rather than 'portal_client'?
            #block = yield portal_client.future_targets(sb_id)
            block = yield client.future_targets(sb_id)
            blocks.append(block)
        # TODO: do something interesting with schedule blocks
        raise tornado.gen.Return(blocks)

    @tornado.gen.coroutine
    def _get_sensor_values(self, product_id, targets):
        """Gets sensor values associated with the product_id's subarray

        Args:
            product_id (str): the product id of a currently activated subarray
            targets (list): expressions to look for in sensor names

        Returns:
            A dictionary of sensor-name / value pairs

        Examples:
            >>> self.io_loop.run_sync(lambda: self._get_sensor_values(product_id, ["target", "ra", "dec"]))
        """
        sensors_and_values = dict()
        if not targets:
            logger.warning("Sensor list empty. Not querying katportal...")
            raise tornado.gen.Return(sensors_and_values)
        client = self.subarray_katportals[product_id]
        sensor_names = yield client.sensor_names(targets)
        if not sensor_names:
            logger.warning("No matching sensors found!")
        else:
            for sensor_name in sensor_names:
                try:
                    sensor_value = yield client.sensor_value(sensor_name, include_value_ts=True)
                    sensors_and_values[sensor_name] = self._convert_SensorSampleValueTs_to_dict(sensor_value)
                except SensorNotFoundError as exc:
                    print("\n", exc)
                    continue
            # TODO: get more information using the client?
        raise tornado.gen.Return(sensors_and_values)

    def _convert_SensorSampleValueTs_to_dict(self, sensor_value):
        """Converts the named-tuple object returned by sensor_value
            query into a dictionary. This dictionary contains the following values:
                - timestamp:  float
                    The timestamp (UNIX epoch) the sample was received by CAM.
                    Timestamp value is reported with millisecond precision.
                - value_timestamp:  float
                    The timestamp (UNIX epoch) the sample was read at the lowest level sensor.
                    value_timestamp value is reported with millisecond precision.
                - value:  str
                    The value of the sensor when sampled.  The units depend on the
                    sensor, see :meth:`.sensor_detail`.
                - status:  str
                    The status of the sensor when the sample was taken. As defined
                    by the KATCP protocol. Examples: 'nominal', 'warn', 'failure', 'error',
                    'critical', 'unreachable', 'unknown', etc.

            Args:
                sensor_value (SensorSampleValueTs)

            Returns:
                (dict)
        """
        sensor_value_dict = dict()
        sensor_value_dict['timestamp'] = sensor_value.timestamp
        sensor_value_dict['value_timestamp'] = sensor_value.value_timestamp
        sensor_value_dict['value'] = sensor_value.value
        sensor_value_dict['status'] = sensor_value.status
        return sensor_value_dict

    def _print_start_image(self):
        print(R"""
       ________________________________
      /                                "-_
     /      .  |  .                       \
    /      : \ | / :                       \
   /        '-___-'                         \
  /_________________________________________ \
       _______| |________________________--""-L
      /       F J                              \
     /       F   J                              L
    /      :'     ':                            F
   /        '-___-'                            /
  /_________________________________________--"
+-------------------------------------------------+
|                                                 |
|              Breakthrough Listen's              |
|                                                 |
|                KATPortal Client                 |
|                                                 |
|                 Version: {}                    |
|                                                 |
|  github.com/ejmichaud/meerkat-backend-interface |
|                                                 |
+-------------------------------------------------+
""".format(self.VERSION))

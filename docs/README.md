# Breakthorugh Listen User Supplied Equipment (BLUSE) Stack at MeerKAT

This documentation details the design of Breakthrough Listen's hardware and software systems at MeerKAT. At a high level, observation data and metadata flows through the network as indicated in the below diagram: 

<img src="images/diagram.png">

In the above diagram we see the following components:

## CAM
The **C**ontrol **A**nd **M**onitoring computers at MeerKAT. These are not maintained by us, but are what we interface with to acquire metadata.

## [KATCP Server](KATCP.md)
The `KATCP Server` receives signals from `CAM`. These requests include:

```
configure, capture-init, capture-start, capture-stop, capture-done, deconfigure, halt, help, log-level, restart [#restartf1]_, client-list, sensor-list, sensor-sampling, sensor-value, watchdog, version-list (only standard in KATCP v5 or later), request-timeout-hint (pre-standard only if protocol flags indicates timeout hints, supported for KATCP v5.1 or later), sensor-sampling-clear (non-standard)
```
The `?configure` `?capture-init` `?capture-start` `?capture-stop` `?capture-done` `?deconfigure` and `?halt` requests have custom implementations in `src/katcp_server.py`'s `BLBackendInterface` class. The rest are inherited from its superclass. Together, these requests (particularly `?configure`) contain important metadata, such as the URLs for the raw voltage data coming off the telescope, and their timing is important too. For instance, we'll know when an observation has started when we receive the `?capture-start` request. For more information, see the [ICD](https://docs.google.com/document/d/19GAZYT5OI1CLqoWU8Q2urBUYyTVfvWktsH4yTegrF_0/edit) and the [Swim Lane Diagram](https://docs.google.com/spreadsheets/d/1U9Un2jd3GsgTeaJ96GhQPXckZkG_TdRd0DCsaxFeX3Q/edit#gid=0)

## [Redis Server](REDIS_DOCUMENTATION.md)
A redis database is a key-value store that is great for sharing information between modules in a system like this. It runs as a server on the local network that can be modified and accessed via requests. It has a command-line client, but the [redis-py](https://github.com/andymccurdy/redis-py) python module is how we interface with it within our python code.

## [Katportal Client](KATPortalClient.md)
The `Katportal Client` sends requests for additional metadata to `CAM`. 

## [Distributor](distributor.md)
Publishes information to 64 Redis channels, which will be subscribed to by the compute nodes.

## Usage
After starting redis on port 6379, simply start both modules like so:
```
(venv)$ python katcp_start.py
```
Which will run the server locally on port 5000, and:
```
(venv)$ python katportal_start.py
```
Which will start the katportal querying system.

Both of these processes need to be running to properly acquire all observational metadata.

## Redis Formatting:
For redis key formatting and respective value descriptions, see [REDIS_DOCUMENTATION](REDIS_DOCUMENTATION.md)

## Next Steps:
*There are a range of additions and modifications that you will have to make before deploying. The reason why many of these have been left out is that as of 2018-08-06, I simply don't have enough information about the needs of Breakthrough Listen to build them. Here's what you should keep in mind:*

### Big Things:
* The `Katportal Client` module is currently designed to query for specific sensors **only once** in response to the `KATCP Server` receiving a request. For instance, when we receive a `?capture-start` request, `src/katcp_server.py` publishes a `capture-start:[product_id]` message to the `alerts` redis channel. This message is then received by `src/katportal_server.py` and a set of sensor values are retrieved through the `Katportal`. My concerns about this method are that sensor values may change in ways that we care about after we send this request. A possibly safer method, which is the only method  mentioned in the [Swim Lane Diagram](https://docs.google.com/spreadsheets/d/1U9Un2jd3GsgTeaJ96GhQPXckZkG_TdRd0DCsaxFeX3Q/edit#gid=0), is to use a websocket subscription to get sensor data. Websocket subscriptions are implemented, to a limited degree, in the `scripts/subscribe.py` script, but we may want to build subscriptions in to the `src/katportal_server.py`'s `BLKATPortalClient` by default. 
* Even if you don't care about subscriptions, you'll still need to make additions to the `src/katportal_server.py` file to specify which sensors to query in response to which events. For instance, to get data from all sensors containing `target` in their name, add the string `"target"` to the `sensors_to_query` list in the `_capture_init` method. These strings can also be regular expressions, as mentioned in the [Katportal Docs](https://docs.google.com/document/d/1BD22ZwaVwHiB6vxc0ryP9vUXnFAsTbmD8K2oBPRPWCo/edit). 
<div align="center">
  <img src="https://ericjmichaud.com/other/seti/images/katportal_code_sample.png" align="center" width="80%">
</div>

* Currently, sensor values are stored in redis associated with the `product_id` of the subarray which they were queried from (see [REDIS_DOCUMENTATION](REDIS_DOCUMENTATION.md)). Since product ids are temporary, this could lead to a massive build-up of outdated sensor values in the redis server, since a new key is created for each product_id * for each sensor. This could add up quickly! Consider setting an expiration on the keys created within `src/katportal_server.py`, by passing an `expiration` (in seconds) named argument to `write_pair_redis`. 

### Smaller Things:
* Currently, `katportal_start.py` does not shut down in a thread-safe way. `katcp_start.py` manages to do this, but it uses a complex mechanism that I don't understand. Consider supporting thread-safe shutdown of `src/katportal_server.py`'s io_loop in the future.
* While currently commented out, there is a mechanism that sends a slack message when either of the modules shuts down. For testing purposes, this has been commented out. When you deploy, you should uncomment it, and possibly modify its behavior. As you can see in the `src/slack_tools.py` file, using this requires you to store a Unix variable called `$SLACK_TOKEN` in your local environment. 

**Tasks are marked in the code with a `TODO` keyword. Search for them like this:**
```
$ grep -r -n TODO .

./scripts/subscribe.py:56:    # TODO: Add sensors to subscribe to on ?configure request
./katportal_start.py:11:    # TODO: uncomment when you deploy
./src/katcp_server.py:349:            default=True, # TODO: implement actual NTP synchronization request
./src/katcp_server.py:372:        TODO:
./src/katcp_server.py:388:        # TODO: uncomment when you deploy
./src/katportal_server.py:36:    TODO:
./src/katportal_server.py:87:        sensors_to_query = [] # TODO: add sensors to query on ?configure
./src/katportal_server.py:106:        sensors_to_query = [] # TODO:  add sensors to query on ?capture_init
./src/katportal_server.py:122:        # TODO: get more information?
./src/katportal_server.py:142:        # TODO: get more information?
./src/katportal_server.py:153:        sensors_to_query = [] # TODO: add sensors to query on ?capture_done
./src/katportal_server.py:169:        sensors_to_query = [] # TODO: add sensors to query on ?deconfigure
./src/katportal_server.py:211:        # TODO: do something interesting with schedule blocks
./src/katportal_server.py:245:            # TODO: get more information using the client?
``` 

## Questions:

1. In [1], Siemion et al. say that the "SETI Search Subsystem" will detect candidate signals in **real time**. What needs to happen from a software perspective for this to happen? Will those processes be started and monitored from my system, or from something lower in the stack?
2. A **significant task** seems to be the design of the software-based beamforming/interferometry systems. In [1], Siemion et al. say that our system will start with a single beam and then upgrade from there. Do we still plan on scaling this way? If so, do we intend on writing the software now that will support the multi-beam observing when it comes online? Will the system that we are building now be sufficiently general to handle all sub-array sizes and beam configurations going forward?
3. In [1], Siemion et al. write that "A small amount of observing time or follow up observations, 5-10 hours per month, would significantly improve the speed and productivity of the commensal program." What kind of human interface do we need to build in order to accomodate these observations? Will these targets be selected manually (in contrast to the automated "scheduling" system that will do most of our commensal observing)?
4. **Will this same software be used on the SKA? (approx. 2022?)**

## References

1. [SETI on MeerKAT Project Proposal, Siemion et al.](https://www.overleaf.com/5968578fnxfyc#/19819904/)
2. [katcp-python GitHub repository](https://github.com/ska-sa/katcp-python)
3. [katportalclient GitHub repository](https://github.com/ska-sa/katportalclient)
4. [MeerKAT ICD](https://docs.google.com/document/d/19GAZYT5OI1CLqoWU8Q2urBUYyTVfvWktsH4yTegrF_0/edit#)
5. [TRAPUM-CAM Interface](https://github.com/ewanbarr/reynard/tree/refactor)
6. [Swim Lane Diagram](https://docs.google.com/spreadsheets/d/1U9Un2jd3GsgTeaJ96GhQPXckZkG_TdRd0DCsaxFeX3Q/edit#gid=0)
7. [Katportal Docs](https://docs.google.com/document/d/1BD22ZwaVwHiB6vxc0ryP9vUXnFAsTbmD8K2oBPRPWCo/edit). 
8. [REDIS_DOCUMENTATION](REDIS_DOCUMENTATION.md)

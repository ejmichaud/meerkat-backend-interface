# meerkat-backend-interface

This repository is for the `KATCP Server` and `Katportal Client` modules of the below diagram. Together, these modules extract all observational metadata to enable Breakthrough Listen's commensal observing program at the MeerKAT telescope. These data include:
* URLs of SPEAD packet streams containing raw voltage data, to be subscribed to by our Beam Former.
* current target information
* schedule block information
* antenna weights
* etc... (TODO: add more)

###  Diagram of Breakthrough Listen To-Be-Built Software Stack at MeerKAT
```
        +----------+
        |          |
        |  KATCP   | Requests containing metadata
        |  Server  | <------------------------+
        |          |                          |
        +--+-------+                          |               ,-.
           |                                  |              / \  `.  __..-,O
           |                                  |             :   \ --''_..-'.'
           v                                  |             |    . .-' `. '.
                                              |             :     .     .`.'
        +----------+                     +----+-----+        \     `.  /  ..
        |          |                     |          |         \      `.   ' .
        |  Redis   |                     |          | +------> `,       `.   \
+-------+  Server  |                     |   CAM    |          ,|,`.       `-.\
|       |          |                     |          |        '.||  ``-...__..-`
|       +------+---+                     |          | <-----+  |  |
|              |                         +----+--+--+          |__|
|          ^   |                              ^  |             /||\
|          |   v                              |  |            //||\\
|          |                                  |  |           // || \\
|       +--+--------+                         |  |       ___//__||__\\___
|       |           | Requests for metadata   |  |       '--------------'
|       | Katportal +-------------------------+  |               |
|       | Client    |           metadata         |               |
|       |           | <--------------------------+               |
|       +-----------+                                            |
|                                                                |
|                                                                |
+------------+-------------------------+                         |
             |                         |                         |
             |                         |                         |
             v                         v                         |
        +----+------+             +----+------+                  |
        | Real-time |             | Target    |                  |
        | Signal    |             | Selection |   raw voltage    |
        | Detection | <-----------+ &         | <----------------+
        | and Data  |             | Beam      |      stream
        | Storage   |             | Forming   |
        +-----------+             +-----------+
```

## Description of modules in above diagram:

### Telescope ASCII Art:
Represents the actual antennas at the telescope. There are 64 of them.

### CAM
The **C**ontrol **A**nd **M**onitoring computers for the telescope. These are not maintained by us, but are what we interface with to acquire metadata.

### KATCP Server
The `KATCP Server` receives requests from `CAM`. These requests include:

* ?configure
* ?capture-init
* ?capture-start
* ?capture-stop
* ?capture-done
* ?deconfigure
* ?halt
* ?help
* ?log-level
* ?restart [#restartf1]_
* ?client-list
* ?sensor-list
* ?sensor-sampling
* ?sensor-value
* ?watchdog
* ?version-list (only standard in KATCP v5 or later)
* ?request-timeout-hint (pre-standard only if protocol flags indicates timeout hints, supported for KATCP v5.1 or later)
* ?sensor-sampling-clear (non-standard)

The `?configure` `?capture-init` `?capture-start` `?capture-stop` `?capture-done` `?deconfigure` and `?halt` requests have custom implementations in `src/server.py`'s `BLBackendInterface` class. The rest are inherited from its superclass. Together, these requests (particularly `?configure`) contain important metadata, such as the URLs for the raw voltage data coming off the telescope, and their timing is important too. For instance, we'll know when an observation has started when we receive the `?capture-start` request.

### Redis Server
A redis database is a key-value store that is great for sharing information between modules in a system like this. It runs as a server on the local network that can be modified and accessed via requests. It has a command-line client, but the [redis-py](https://github.com/andymccurdy/redis-py) python module is how we interface with it within our python code.

### Katportal Client
The `Katportal Client` sends requests for additional metadata to `CAM`. 

### Target Selection & Beam Forming
System that selects targets from and forms pencil-beams to observe them. NOT YET BUILT, however our target list has been compiled by Logan Pierce :star:

### Real-time Signal Detection and Data Storage
Our signal detection and data storage systems.

## Installation Instructions

First, make sure to [install redis](https://redis.io/topics/quickstart). If it's installed, you should be able to start it by executing:
```
$ redis-server
```
Next, download the repository like so:
```
$ git clone --recurse-submodules https://github.com/ejmichaud/meerkat-backend-interface
```
And enter the repository with 
```
$ cd meerkat-backend-interface
```
Next, create a Python 2 virual environment like so:
```
virtualenv -p /usr/bin/python venv
```
Now, simply activate your virtual environment and install the package like so:
```
$ source venv/bin/activate
(venv)$ pip install .
```
This will install all dependencies.

## Usage
Simply start both modules like so:
```
(venv)$ python katcp_start.py
```
Which will run the server locally on port 5000, and:
```
(venv)$ python katportal_start.py
```
Which will start the katportal querying system.

Both of these processes need to be running to properly acquire all observational metadata.

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
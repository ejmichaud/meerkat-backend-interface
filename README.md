# meerkat-backend-interface
Breakthrough Listen's backend interface to CAM at MeerKAT.

## Diagram of Breakthrough Listen To-Be-Built Software Stack at MeerKAT

```
                                                   +-------------+
                                                   |             |
                               +-------------------+     CAM     |
                               |                   |             |
                               |                   +--+--+-------+
                               |                      |  ^
                               |                      |  |
                               v                      |  |
                         +-----+-----+                |  |
                         | Metadata  |                v  +
                         | Interface |              ,-.
                         +-----+-----+             / \  `.  __..-,O
                               |                  :   \ --''_..-'.'
                               |                  |    . .-' `. '.
                               |                  :     .     .`.'
                               v                   \     `.  /  ..
+-----------+            +-----+-----+              \      `.   ' .
| Real-time |            | Target    |               `,       `.   \
| Signal    |            | Selection |               ,|,`.       `-.\
| Detection +<-----------+ &         +<----------+ '.||  ``-...__..-`
| and Data  |            | Beam      |               |  |
| Storage   |            | Forming   |               |__|
+-----------+            +-----------+               /||\
                                                    //||\\
                                                   // || \\
                                               ___//__||__\\___
                                               '--------------'
```

## Description
This repository is for the "Metadata Interface" module of the above diagram. This will interface with the MeerKAT-facility monitor, control and scheduling systems, and extract all necessary observational metadata needed for instantiating and operating the real-time beamforming system and appropriately labeling science data products. It will (in all likelihood) run a KATCP client server that retrieves data from CAM and records / publishes it to a redis server.


## Questions:

1. In [1], Siemion et al. note that a simulation environment will be constructed at ATA to mimick MeerKAT. This was supposed to be finished in 2016. What is the status of this project?
2. In [1], Siemion et al. say that the "SETI Search Subsystem" will detect candidate signals in **real time**. What needs to happen from a software perspective for this to happen? Will those processes be started and monitored from my system, or from something lower in the stack?
3. A **significant task** seems to be the design of the software-based beamforming/interferometry systems. In [1], Siemion et al. say that our system will start with a single beam and then upgrade from there. Do we still plan on scaling this way? If so, do we intend on writing the software now that will support the multi-beam observing when it comes online? Will the system that we are building now be sufficiently general to handle all sub-array sizes and beam configurations going forward?
4. In [1], Siemion et al. write that "A small amount of observing time or follow up observations, 5-10 hours per month, would significantly improve the speed and productivity of the commensal program." What kind of human interface do we need to build in order to accomodate these observations? Will these targets be selected manually (in contrast to the automated "scheduling" system that will do most of our commensal observing)?
5. **Will this same software be used on the SKA?**
6. How do [2] and [3] fit into the project? What is different about these two libraries? They both seem to enable users to request data with the KATCP protocol from the MeerKAT front-end.
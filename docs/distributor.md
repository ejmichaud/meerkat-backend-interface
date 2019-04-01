# Distributor

The "distributor" module orchestrates the activity of the compute nodes by parsing Redis and *distributing* information across 64 Redis channels that are subscribed to by each compute node. The most significant type of info that it sends are SPEAD stream addresses that need to be subscribed to by the compute nodes, however other types of message can be programmed too. 


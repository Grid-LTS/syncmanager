## Sync  Manager (Python3)

(in Progress)

### Description
This is a version of the Sync Job Manager (for Bash) written in python 3. This script automates the task of syncing folders and projects (databases) on client computers with a central server. It builds on other software for data synchronization between distributed systems.
At the moment support for Git & Unison is implemented, but other protocols like rsync are planned for the future.
In case of Git **all** branches in for those projects, which are stated in the *.conf files, will be synced with the server.  


### Currently planned
- lock files
- specify if only push, only pull or both modes are applied to each repo
- gui for convenient setup of conf files
- error report in case of conflicts or failed checkouts
At the moment the script is simple and not laid out to sync in collaborative projects. E.g. in case of git, when pushing the server branches are expected to be fast-fowarded. The same applies to pulling.
Merges cannot be handled. In the future this should be possible.

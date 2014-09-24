By and large, the project organizer does not need much by way of migration. Aside from bower installs and the like,
the one migration task is to add a field to all the nodes called is_folder and to make it False.

Run the script from the root of the OSF directory. The logic is tested, but authentication is not, so there might
need to be a small fix for that. Dev doesn't have authentication for mongo, so the authentication was untestable.
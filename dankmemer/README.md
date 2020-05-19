# Information on self hosting an imgen instance.

Imgen is the name given to the image generator that powers Dank Memers image manipulation services. This service is open source and is found on their repo. Do the digging yourself to find out. This will have the basic steps on how to host an instance. Nothing indept, but enough to get going.

---

Start by cloning the repo to your machine.

Requirements:
rethinkdb
redis, everything in the requirements.txt

---

rethinkdb requires a database named "imgen" and inside that it must have two tables named "keys" and "applications"

If you're just hosting for that machine, the next step does not apply.

- Change the address in the start script to 0.0.0.0

Start the server using the start script provided.

## Yes, this guide isn't detailed. If you want to host it then I expect you to know what you're doing. What I listed was some information not seen on their repo.
## If you do not know then you can apply for a key at mine or any public imgen out there.

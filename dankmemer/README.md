# Information on self hosting an imgen instance.

Imgen is the name given to the image generator that powers Dank Memers image manipulation services. This service is open source and is found on their repo. Do the digging yourself to find out. This will have the basic steps on how to host an instance. Nothing indept, but enough to get going.

---

Start by first making a venv. Making a venv is highly recommended. You can host imgen inside the same venv you're hosting your redbot instance on OR you can create a new venv and setup imgen there. It's completely your choice.
[Read this if you don't know how to create a venv](https://docs.discord.red/en/stable/install_linux_mac.html#creating-venv-linux).

Before you activate your venv, make sure you installed ImageMagik, if you didn't please check out [this guide](https://docs.wand-py.org/en/0.4.1/guide/install.html) and install that, you will also need rethinkdb from [here](https://rethinkdb.com/docs/install/) depending on your linux distribution or docker, whichever you prefer.
Also install `redis-server` for your linux distribution. If you're using Ubuntu 18.04 or above, you can follow [this guide](https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-redis-on-ubuntu-18-04).

Now that you have created venv, activate it with:
```
source ~/path/to/venv/activate
```

Once you're inside venv, start by cloning the dank memer imgen repo and finishing the setup:
```
git clone https://github.com/DankMemer/imgen
cd imgen/

# now copy the config.json

cp -rf example-config.json config.json

# open config.json and fill in the necessary credentials and save it.
# Now to install the requirements

python -m pip install --upgrade pip
pip install gunicorn
pip install -r requirements.txt
```

Now that is done, `rethinkdb` requires a database named "imgen" and inside that it must have two tables named "keys" and "applications"
You can create them by following this commands in the order one by one:
```py
#this opens a python3 interpreter
python

from rethinkdb import r
r.connect('localhost', 28015).repl()
r.db_create("imgen").run()
r.db('imgen').table_create('keys').run()
r.db('imgen').table_create('applications').run()
exit()
```

If you're just hosting for that machine (i.e. hosting locally), the next step does not apply.

- Change the address in the `start.sh` script from `127.0.0.1` to `0.0.0.0`

Now before starting the start script, go to [Discord Developers](https://discord.com/developers) portal, then go to your Bot Application -> OAuth2 section and add the following redirect in the Redirects field:
```
http://PUBLIC_IP:65535/callback

## replace `PUBLIC_IP` with your host's Public IP.
## you can find your host's `PUBLIC_IP` with following command in your terminal:
wget -qO- ifconfig.me
```
Scroll below on that OAuth2 page, choose any of the scopes you desire and click on Save button.

Start the imgen server using the start script provided:
```
./start.sh
```

At this point, you can visit `http://PUBLIC_IP:65535` to see if the imgen server is running successfully or not. If it's working, go to Admin panel there, generate a new key and copy it then come to Discord and do the following command with your Red bot in a private channel:
```
[p]set api imgen authorization <your_generated_imgen_key>
```
where `[p]` is your bot's prefix and replace `<your_generated_imgen_key>` with the newly generated imgen key you just copied.

Now, download the dankmemer cog and load it and do:
```
#first read the instructions listed at:
[p]dankmemersetup

[p]dmurl http://PUBLIC_IP:65535/api
```

Now do `[p]help DankMemer` to see if your bot lists all the commands this cog has.

NOTE: If you're hosting your Red bot instance on Amazon AWS, you need to enable traffic from ports 80, 443 and 65535 from your AWS console -> Security Groups and you also need to enable those ports from your system/VPS firewall otherwise you won't be able to access your Public IP. Google it if you don't know how to do it.

## Yes, this guide isn't extremely detailed. If you want to host it then I expect you to know what you're doing. What I listed was some information not seen on their repo.

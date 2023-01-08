Mastodon User Count Bot
=======================

A bot which counts users from all instances listed at https://instances.social
then posts statistics to [Mastodon](https://github.com/tootsuite/mastodon).

My copy is currently running at https://bitcoinhackers.org/@mastodonusercount

### Dependencies

-   **Python 3**
-   [gnuplot](http://www.gnuplot.info/) version 5 or greater, for example: `sudo apt install gnuplot5-qt` or `sudo apt install gnuplot5-x11` or `sudo apt install gnuplot-qt` will work
-   [Mastodon.py](https://github.com/halcy/Mastodon.py): `pip3 install Mastodon.py`
-   A recent version of `requests` is needed for socks5h proxy: you can update with `sudo -H easy_install3 -U pip`, `pip3 install requests --upgrade` and `pip3 install pysocks`

### Usage:

1. Create a file called `config.txt` to specify the hostname of the Mastodon instance you would like to post statistics. It must be in json format, see `config.txt.example`.
2. Fill out client id, client secret and access token in `config.txt` as follows:

```
{
	"mastodon_hostname": "mastodon.social",
	"client_id": "<your client ID>",
	"client_secret": "<your client secret>",
	"access_token": "<your access token>"
}
```

To get these values, create an account for your bot, then run this script:

```python
from mastodon import Mastodon

# change this to the apprpriate instance, login and username
instance_url = "https://mastodon.social"
user_name = "youremail@example.com"
user_password = "123456"

Mastodon.create_app("My User Count", scopes=["read","write"],
   to_file="clientcred.txt", api_base_url=instance_url)

mastodon = Mastodon(client_id = "clientcred.txt", api_base_url = instance_url)
mastodon.log_in(
   user_name,
   user_password,
   scopes = ["read", "write"],
   to_file = "usercred.txt"
)
```

Your client id and secret are the two lines in `clientcred.txt`, your access
token is the line in `usercred.txt`. (Yeah, I know I should have automated this step --
but hey, the above script is better than having to figure it out by yourself! ;) )

3. Use your favorite scheduling method to set `./crawler.py` and `./publish.py` to run regularly.

The `./crawler.py` handles all the data:
- regularly queries https://instances.social and merges the received instances into `list.json`
- visits all available instances and saves their data into `snapshot.json`
- records historical data in `mastostats.csv`

`./crawler.py` ideally called four times an hour: it tries to reach each instance over http, https, clearnet and darknet.

`./publish.py`  was designed to run once in every hour, and it draws a graph and publishes it at Mastodon.

Note: The script will fail to output a graph until you've collected data points that are actually different!

### Tips
If you like this project, help to keep it alive! Thank you for your support!

[![tippin.me](https://badgen.net/badge/%E2%9A%A1%EF%B8%8Ftippin.me/@gallizoli/F0918E)](https://tippin.me/@gallizoli)

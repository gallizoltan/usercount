Mastodon User Count Bot
=======================

A bot which counts users from all instances listed at https://instances.social
then posts statistics to [Mastodon](https://github.com/tootsuite/mastodon).

My copy is currently running at https://bitcoinhackers.org/@mastodonusercount

### Dependencies

-   **Python 3**
-   [gnuplot](http://www.gnuplot.info/) version 5 or greater, for example: `sudo apt install gnuplot5-qt` or `sudo apt install gnuplot5-x11` will work
-   [Mastodon.py](https://github.com/halcy/Mastodon.py): `pip3 install Mastodon.py`
-   A recent version of `requests` may be needed for socks5h proxy: `sudo -H easy_install3 -U pip`, `pip3 install requests --upgrade` and `pip3 install pysocks`
-   Everything else at the top of `usercount.py`!

### Usage:

1. Create a file called `config.txt` to specify the hostname of the Mastodon instance you would like to post statistics. It must be in json format, see `config.txt.example`.
2. Fill out client id, client secret and access token in `config.txt` as follows:

```
{
	"mastodon_hostname": "mastodon.social",
	"client_id": "<your client ID>",
	"client_secret": "<your client secret>",
	"access_token": "<your access token>",
	"backup_folder": "<your backup folder - optional>"
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

3. Use your favourite scheduling method to set `./usercount.py` to run regularly.

Call the script with the `--no-upload` argument if you don't want to upload anything.

The script was designed to run once in every hour. Call with the `--no-update` argument if you run more often than one hour, so it will not collect any additional information.

Note: The script will fail to output a graph until you've collected data points that are actually different!

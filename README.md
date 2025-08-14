# KWinIdleTime

A set of scripts that work together to let you run programs whenever you are away from your computer.

### Quick Notice

Since these scripts use DBus to communicate (partially intentionally and partially mandatory), any program can see when you move your mouse (Not where!) if you use these scripts. You can adjust how often mouse pings are sent by editing [kwin_script/contents/code/main.js](https://github.com/Kale-Ko/KWinIdleTime/blob/main/kwin_script/contents/code/main.js) but this only reduces the problem and potentially means missing mouse movements.

## Installation

Clone the repository with `git clone https://github.com/Kale-Ko/KWinIdleTime` and then cd into the new repository and run `make install`.
This will install the scripts into `/usr/local/share/kwinidletime/` and the services into `/usr/local/lib/systemd/user/`.
Reboot and it should start running!

It is also possible to produce entirely self contained executables using pyinstaller, simply run `make build` and they will be placed in `dist/`. They can get a bit large but have the benefit of not even requiring Python to be install to run.

## Uninstallation

You can undo an installation completely by running `make uninstall`.

## Configuration

The environment config and listener scripts are placed in `$XDG_CONFIG_HOME/kwinidletime/` and `$XDG_CONFIG_HOME/kwinidletime/listeners/` respectively. `$XDG_CONFIG_HOME` is usually `$HOME/.config/`.

### Environment

The environment config (`$XDG_CONFIG_HOME/kwinidletime/config`) currently only has one value.

`KWINIDLETIME_THRESHOLD` - The number of seconds it takes for the daemon to mark you as idle.

*Note*: this config only effects the Systemd services, for other instances you need to adjust your commandline.

### Listener Scripts

Listener scripts are just any file in the `listeners/` directory that is executable. They will be executed one by one in the same way they would be if you did `./script` in a shell (using binfmt/shebangs).

When a user goes idle, scripts will be passed the single argument "idle".
When a user becomes active again, scripts will be passed two arguments, "active" and the number of seconds the user was idle for.

The listener directory and all scripts must have the permissions `0500` to be executed.

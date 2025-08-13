build: build_daemon build_listener

build_daemon: daemon/main.py
	pyinstaller --clean --noconfirm --onefile --name daemon daemon/main.py --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2 --strip --argv-emulation

build_listener: listener/main.py
	pyinstaller --clean --noconfirm --onefile --name listener listener/main.py --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2 --strip --argv-emulation

install: install_kwin_script

install_kwin_script:
	kpackagetool6 --type=KWin/Script -i kwin_script/

	kwriteconfig6 --file kwinrc --group Plugins --key KWinIdleTimeEnabled true
	qdbus org.kde.KWin /KWin reconfigure

uninstall_kwin_script:
	kpackagetool6 --type=KWin/Script -r KWinIdleTime

reinstall_kwin_script: uninstall_kwin_script install_kwin_script

upgrade_kwin_script:
	kpackagetool6 --type=KWin/Script -u kwin_script/

clean:
	rm -rf build/
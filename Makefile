build: build_daemon build_listener build_combined

build_daemon: python/daemon.py
	pyinstaller --clean --noconfirm --onefile --name daemon python/daemon.py --add-data ../python/io.github.kale_ko.KWinIdleTime.xml:./ --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2

build_listener: python/listener.py
	pyinstaller --clean --noconfirm --onefile --name listener python/listener.py --add-data ../python/io.github.kale_ko.KWinIdleTime.xml:./ --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2

build_combined: python/combined.py
	pyinstaller --clean --noconfirm --onefile --name combined python/combined.py --add-data ../python/io.github.kale_ko.KWinIdleTime.xml:./ --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2

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
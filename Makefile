build: build_daemon build_listener build_combined

build_daemon: dist/daemon
dist/daemon: python/daemon.py python/io.github.kale_ko.KWinIdleTime.xml
	pyinstaller --clean --noconfirm --onefile --name daemon python/daemon.py --add-data ../python/io.github.kale_ko.KWinIdleTime.xml:./ --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2

build_listener: dist/listener
dist/listener: python/listener.py python/io.github.kale_ko.KWinIdleTime.xml
	pyinstaller --clean --noconfirm --onefile --name listener python/listener.py --add-data ../python/io.github.kale_ko.KWinIdleTime.xml:./ --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2

build_combined: dist/combined
dist/combined: python/combined.py python/io.github.kale_ko.KWinIdleTime.xml
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
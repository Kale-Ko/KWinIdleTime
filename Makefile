build: build_daemon build_listener build_combined

build_daemon: dist/daemon
dist/daemon: python/daemon.py python/io.github.kale_ko.KWinIdleTime.xml
	pyinstaller --clean --noconfirm --onefile --name daemon python/daemon.py --add-data ../python/io.github.kale_ko.KWinIdleTime.xml:./ --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2

build_listener: dist/listener
dist/listener: python/listener.py python/io.github.kale_ko.KWinIdleTime.xml
	pyinstaller --clean --noconfirm --onefile --name listener python/listener.py --add-data ../python/io.github.kale_ko.KWinIdleTime.xml:./ --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2

build_combined: dist/combined
dist/combined: python/combined.py python/daemon.py python/listener.py python/io.github.kale_ko.KWinIdleTime.xml
	pyinstaller --clean --noconfirm --onefile --name combined python/combined.py --add-data ../python/io.github.kale_ko.KWinIdleTime.xml:./ --distpath dist/ --workpath build/ --specpath build/ --noconsole --optimize 2

install: install_scripts install_services install_kwin_script

install_data:
	sudo install -Dm644 python/io.github.kale_ko.KWinIdleTime.xml -t /usr/local/share/kwinidletime/

install_scripts: install_data python/daemon.py python/listener.py python/combined.py
	sudo install -Dm755 python/daemon.py -t /usr/local/share/kwinidletime/
	sudo install -Dm755 python/listener.py -t /usr/local/share/kwinidletime/
	sudo install -Dm755 python/combined.py -t /usr/local/share/kwinidletime/

install_binaries: install_data build dist/daemon dist/listener dist/combined
	sudo install -Dm755 dist/daemon -t /usr/local/share/kwinidletime/
	sudo install -Dm755 dist/listener -t /usr/local/share/kwinidletime/
	sudo install -Dm755 dist/combined -t /usr/local/share/kwinidletime/

install_services: install_scripts data/kwinidletime_daemon.service data/kwinidletime_listener.service data/kwinidletime_combined.service
	cp data/kwinidletime_daemon.service /tmp/kwinidletime_daemon.service
	cp data/kwinidletime_listener.service /tmp/kwinidletime_listener.service
	cp data/kwinidletime_combined.service /tmp/kwinidletime_combined.service

	sed -i 's|%{install_dir}|/usr/local/share/kwinidletime|' /tmp/kwinidletime_daemon.service /tmp/kwinidletime_listener.service /tmp/kwinidletime_combined.service
	sed -i 's|%{config_dir}|%E/kwinidletime/listeners|' /tmp/kwinidletime_daemon.service /tmp/kwinidletime_listener.service /tmp/kwinidletime_combined.service

	sudo install -Dm644 /tmp/kwinidletime_daemon.service -t /usr/local/lib/systemd/user/
	sudo install -Dm644 /tmp/kwinidletime_listener.service -t /usr/local/lib/systemd/user/
	sudo install -Dm644 /tmp/kwinidletime_combined.service -t /usr/local/lib/systemd/user/
	rm -f /tmp/kwinidletime_daemon.service /tmp/kwinidletime_listener.service /tmp/kwinidletime_combined.service

	systemctl --user daemon-reload
	systemctl --user enable kwinidletime_combined.service

uninstall: uninstall_kwin_script
	systemctl --user disable --now kwinidletime_combined.service || true
	systemctl --user disable --now kwinidletime_listener.service || true
	systemctl --user disable --now kwinidletime_daemon.service || true

	sudo rm -f /usr/local/lib/systemd/user/kwinidletime_combined.service
	sudo rm -f /usr/local/lib/systemd/user/kwinidletime_listener.service
	sudo rm -f /usr/local/lib/systemd/user/kwinidletime_daemon.service

	sudo rm -rf /usr/local/share/kwinidletime/

install_kwin_script: kwin_script/metadata.json kwin_script/contents/code/main.js
	kpackagetool6 --type=KWin/Script -i kwin_script/

	kwriteconfig6 --file kwinrc --group Plugins --key KWinIdleTimeEnabled true
	qdbus org.kde.KWin /KWin reconfigure

uninstall_kwin_script:
	kpackagetool6 --type=KWin/Script -r KWinIdleTime

reinstall_kwin_script: uninstall_kwin_script install_kwin_script

upgrade_kwin_script: kwin_script/metadata.json kwin_script/contents/code/main.js
	kpackagetool6 --type=KWin/Script -u kwin_script/

clean:
	rm -rf build/
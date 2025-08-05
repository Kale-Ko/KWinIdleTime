install_kwin_script:
	kpackagetool6 --type=KWin/Script -i kwin_script/

	kwriteconfig6 --file kwinrc --group Plugins --key KWinIdleTimeEnabled true
	qdbus org.kde.KWin /KWin reconfigure

uninstall_kwin_script:
	kpackagetool6 --type=KWin/Script -r KWinIdleTime

reinstall_kwin_script: uninstall_kwin_script install_kwin_script

upgrade_kwin_script:
	kpackagetool6 --type=KWin/Script -u kwin_script/
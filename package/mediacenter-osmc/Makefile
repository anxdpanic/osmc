all:
	@echo "Specify a target:\nmake rbp1\nmake rbp2\nmake vero2\nmake vero3\nmake pc"

rbp1:
	sudo bash build.sh "rbp1"

rbp2:
	sudo bash build.sh "rbp2"

vero2:
	sudo bash build.sh "vero2"

vero3:
	sudo bash build.sh "vero3"

pc:
	sudo bash build.sh "pc"

clean:
	sudo rm -f *.deb > /dev/null 2>&1
	sudo rm -rf files/usr > /dev/null 2>&1
	sudo rm -rf files-debug/usr > /dev/null 2>&1

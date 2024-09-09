all:
	mkdir -p out
	g++ src/main.cpp -o out/transit
	g++ tools/usb/readUSB_linux.cpp -o out/readUSB -lusb-1.0
debug:
	mkdir -p out
	g++ src/main.cpp -o out/transit -g
	g++ tools/usb/readUSB_linux.cpp -o out/readUSB -lusb-1.0 -g
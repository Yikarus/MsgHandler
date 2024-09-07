all:
	mkdir -p out
	g++ src/main.cpp -o out/transit
debug:
	mkdir -p out
	g++ src/main.cpp -o out/transit -g
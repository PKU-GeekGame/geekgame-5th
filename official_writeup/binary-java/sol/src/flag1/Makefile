.PHONY: all

all: Solution.class libsolution.so

Solution.class: Solution.java
	javac $<

Solution.java: libsolution.so Solution.java.template
	python3 to_zlib_bytes.py libsolution.so Solution.java.template > $@

libsolution.so: solution.c
	gcc -O3 -fPIC -shared -I"${JAVA_HOME}/include" -I"${JAVA_HOME}/include/linux" -o $@ $<
	strip $@

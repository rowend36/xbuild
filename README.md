# xbuild
  Xbuild is a minimal android build system that works with a subset of gradle features. It is basically does three things which are downloading of dependencies, arranging the dependencies and invoking command line commands to compile the application. It was made for use on Termux.
  Xbuild is overtly error tolerant. It was made that way because it could not possible implement all of gradle; just enough to fulfil the basic basics. 
  Use with care. It has bugs and given enough time or work, it will fail.

# dependencies
The following binaries should be in your path
-ecj
-aapt
-apksigner
-zipalign
-zipmerge
-python
Optional
-aapt2

Also, you'll need to configure the path to android.jar in build\_utils.py

Kotlin support may or may not be in the works.
To run, call "python xbuild" from your app/ folder. Alternatively, you can call "python xbuild.py <_path to app folder_>. Another module is "python dependency.py [path]" which downloads dependencies.

Most of it can be configured in build\_utils.py.

Feel free to notify me of any issues. Feel more free to fix them yourself. The core principle of xbuild is to be as minimal as possible. In other words, it could have been written in C if that were feasible. Sadly, it is not.

# Todo
-caching of builds - Currently it supports only three build modes, CLEAN, CLEAN\_KEEP\_JARDEX(which rebuilds everything but uses previously dexed libraries where possible) and FAST(which assumes all the dependencies have been built and builds only main).
-limited multithread support.
-stop xbuild from creating junk files in current directory.



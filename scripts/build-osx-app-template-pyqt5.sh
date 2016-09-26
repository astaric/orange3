#!/bin/bash -e
#
# Create (build) an Orange application bundle template
#
# example usage:
#
#   $ build-osx-app-template.sh $HOME/Orange.app
#
# Prerequisites:
#     a working gcc compiler toolchain
#     a working gfortran compiler on PATH


function print_usage () {
echo 'build-osx-app-template.sh [-t] [-k] some_path/Orange.app

Build an Orange application template from scratch.
This will download and build all requirements (Python, Qt5, ...) for a
standalone .app distribution.

Warning: This will take a lot of time.

Options:
    -t --build-temp DIR   A temporary build directory.
    -k --keep-temp        Do not delete the temp directory after build.
    -h --help             Print this help.
'
}

while [[ ${1:0:1} = "-" ]]; do
	case $1 in
		-t|--build-temp)
			BUILD_TEMP=$2
			shift 2
			;;
		-k|--keep-temp)
			KEEP_TEMP=1
			shift 1
			;;
		-h|--help)
			print_usage
			exit 0
			;;
		-*)
			echo "Unknown option $1" >&2
			print_usage
			exit 1
			;;
	esac
done


if [[ $BUILD_TEMP ]]; then
	mkdir -p "$BUILD_TEMP"
else
	BUILD_TEMP=$(mktemp -d -t build-template)
fi

APP=$1

if [[ ! $APP ]]; then
	echo "Target application path must be specified" >&2
	print_usage
	exit 1
fi

mkdir -p "$APP"

# Convert to absolute path
APP=$(cd "$APP"; pwd)

# Get absolute path to the bundle-lite template
SCRIPT_DIR_NAME=$(dirname "$0")
# Convert to absolute path
SCRIPT_DIR_NAME=$(cd "$SCRIPT_DIR_NAME"; pwd)
BUNDLE_LITE=$SCRIPT_DIR_NAME/bundle-lite/Orange.app


# Versions of included 3rd party software

PYTHON_VER=3.5.2
PIP_VER=8.1.2

NUMPY_VER=1.11.1
SCIPY_VER=0.18.0

QT_VER=5.7.0
SIP_VER=4.18.1
PYQT_VER=5.7
SCIKIT_LEARN_VER=0.17.1

# Number of make jobs
MAKE_JOBS=${MAKE_JOBS:-$(sysctl -n hw.physicalcpu)}

PYTHON=$APP/Contents/MacOS/python
EASY_INSTALL=$APP/Contents/MacOS/easy_install
PIP=$APP/Contents/MacOS/pip

export MACOSX_DEPLOYMENT_TARGET=10.8

# You can get older SKDs here: https://github.com/phracker/MacOSX-SDKs/releases
SDK=/Developer/SDKs/MacOSX10.8.sdk

function create_template {
	# Create a minimal .app template with the expected dir structure
	# Info.plist and icons.

	mkdir -p "$APP"
	mkdir -p "$APP"/Contents/MacOS
	mkdir -p "$APP"/Contents/Resources

	# Copy icons and Info.plist
	cp "$BUNDLE_LITE"/Contents/Resources/* "$APP"/Contents/Resources
	cp "$BUNDLE_LITE"/Contents/Info.plist "$APP"/Contents/Info.plist

	cp "$BUNDLE_LITE"/Contents/PkgInfo "$APP"/Contents/PkgInfo

	cat <<-'EOF' > "$APP"/Contents/MacOS/ENV
		# Create an environment for running python from the bundle
		# Should be run as "source ENV"

		BUNDLE_DIR=`dirname "$0"`/../
		BUNDLE_DIR=`perl -MCwd=realpath -e 'print realpath($ARGV[0])' "$BUNDLE_DIR"`/
		FRAMEWORKS_DIR="$BUNDLE_DIR"Frameworks/
		RESOURCES_DIR="$BUNDLE_DIR"Resources/

		PYVERSION="3.5"

		PYTHONEXECUTABLE="$FRAMEWORKS_DIR"Python.framework/Resources/Python.app/Contents/MacOS/Python
		PYTHONHOME="$FRAMEWORKS_DIR"Python.framework/Versions/"$PYVERSION"/

		DYLD_FRAMEWORK_PATH="$FRAMEWORKS_DIR"${DYLD_FRAMEWORK_PATH:+:$DYLD_FRAMEWORK_PATH}

		export PYTHONEXECUTABLE
		export PYTHONHOME
		export PYTHONNOUSERSITE=1

		export DYLD_FRAMEWORK_PATH

		# Some non framework libraries are put in $FRAMEWORKS_DIR by machlib standalone
		export DYLD_LIBRARY_PATH="$FRAMEWORKS_DIR"${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}
		export GVBINDIR="$BUNDLE_DIR"/Resources/graphviz/lib/graphviz
		export PATH="$PATH":"$BUNDLE_DIR"/MacOS
EOF

}

function install_python() {
	download_and_extract "https://www.python.org/ftp/python/$PYTHON_VER/Python-$PYTHON_VER.tgz"

	pushd Python-$PYTHON_VER

	# _hashlib import fails with  Symbol not found: _EVP_MD_CTX_md
	# The 10.5 sdk's libssl does not define it (even though it is v 0.9.7)
	patch setup.py -i - <<-'EOF'
		834c834
		<         min_openssl_ver = 0x00907000
		---
		>         min_openssl_ver = 0x00908000
EOF

	./configure --enable-framework="$APP"/Contents/Frameworks \
				--prefix="$APP"/Contents/Resources \
				--with-universal-archs=intel \
				--enable-ipv6 \
				--enable-universalsdk="$SDK"

	make -j $MAKE_JOBS

	# We don't want to install IDLE.app, Python Launcher.app, in /Applications
	# on the build system.
	make install PYTHONAPPSDIR="$(pwd)"

	popd

	# PythonAppStart will be used for starting the application GUI.
	# This needs to be symlinked here for Desktop services to read the app's
	# Info.plist and not the contained Python.app's
	ln -fs ../Frameworks/Python.framework/Resources/Python.app/Contents/MacOS/Python "$APP"/Contents/MacOS/PythonAppStart
	ln -fs ../Frameworks/Python.framework/Resources/Python.app "$APP"/Contents/Resources/Python.app

	cat <<-'EOF' > "$APP"/Contents/MacOS/python
		#!/bin/bash

		DIRNAME=$(dirname "$0")

		# Set the proper env variables
		source "$DIRNAME"/ENV

		exec -a "$0" "$PYTHONEXECUTABLE" "$@"
EOF

	chmod +x "$APP"/Contents/MacOS/python

	# Test it
	"$PYTHON" -c"import sys, hashlib"

	# Install pip/setuptools
	"$PYTHON" -m ensurepip
	"$PYTHON" -m pip install pip==$PIP_VER

	create_shell_start_script pip
	create_shell_start_script easy_install
}


function install_ipython {
	"$PIP" install ipython
	create_shell_start_script ipython
}

function install_numpy {
	"$PIP" install numpy==$NUMPY_VER

	"$PYTHON" -c"import numpy"
}

function install_pyqt5 {
	"$PIP" install PyQt5==$PYQT_VER

	"$PYTHON" -c"from PyQt5 import QtGui, QtWebEngineWidgets, QtSvg, QtNetwork"
}

function install_scipy {
	# This is tricky (req gfortran)
	"$PIP" install scipy==$SCIPY_VER

	"$PYTHON" -c"import scipy"
}

function install_scikit_learn {
  "$PIP" install scikit-learn==$SCIKIT_LEARN_VER

  "$PYTHON" -c"import sklearn"
}

function install_psycopg2 {
  "$PIP" install psycopg2

  "$PYTHON" -c"import psycopg2"
}

function download_and_extract() {
	# Usage: download_and_extract http://example/source.tar.gz
	#
	# Download the specified .tar source package and extract it in the current dir
	# If the source package is already present only extract it

	URL=$1
	if [[ ! $URL ]]; then
		echo "An url expected"
		exit 1
	fi

	SOURCE_TAR=$(basename "$URL")

	if [[ ! -e $SOURCE_TAR ]]; then
		echo "Downloading $SOURCE_TAR"
		curl --fail -L --max-redirs 3 "$URL" -o "$SOURCE_TAR".part
		mv "$SOURCE_TAR".part "$SOURCE_TAR"
	fi
	tar -xzf "$SOURCE_TAR"
}


function create_shell_start_script() {
	# Usage: create_shell_start_script pip
	#
	# create a start script for the specified script in $APP/Contents/MacOS

	SCRIPT=$1

	cat <<-'EOF' > "$APP"/Contents/MacOS/"$SCRIPT"
		#!/bin/bash

		DIRNAME=$(dirname "$0")
		NAME=$(basename "$0")

		# Set the proper env variables
		source "$DIRNAME"/ENV

		exec -a "$0" "$DIRNAME"/python "$FRAMEWORKS_DIR"/Python.framework/Versions/Current/bin/"$NAME" "$@"
EOF

	chmod +x "$APP"/Contents/MacOS/"$SCRIPT"
}

function cleanup {
	# Cleanup the application bundle by removing unnecesary files.
	find "$APP"/Contents/ \( -name '*~' -or -name '*.bak' -or -name '*.pyc' -or -name '*.pyo' \) -delete

	find "$APP"/Contents/Frameworks -name '*_debug*' -delete
	find "$APP"/Contents/Frameworks -name '*.la' -delete
	find "$APP"/Contents/Frameworks -name '*.a' -delete
	find "$APP"/Contents/Frameworks -name '*.prl' -delete
}

function make_standalone {
	"$PIP" install macholib==1.5.1
	"$PYTHON" -m macholib standalone "$APP"
	"$PIP" uninstall --yes altgraph
	"$PIP" uninstall --yes macholib
}

pushd "$BUILD_TEMP"

echo "Building template in $BUILD_TEMP"
echo

create_template

install_python

install_pyqt5

install_ipython

install_psycopg2

make_standalone

cleanup

popd

if [[ ! $KEEP_TEMP ]]; then
	rm -rf $BUILD_TEMP
fi

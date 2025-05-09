{pkgs ? import <nixpkgs> {}}:
#let
#	packageOverrides = pkgs.callPackage ./python-packages.nix {};
#	python = pkgs.python3.override {inherit packageOverrides; };
#
#
#in
pkgs.mkShell {
  packages = with pkgs; [
    (python311.withPackages (ps:
      with ps; [
        pip
        setuptools
        pandas
        #      numpy
        matplotlib
        requests
        beautifulsoup4
        yfinance
        #      aio_pika
        psycopg2-binary
        sqlalchemy
        apscheduler
        discordpy
        aiohttp # needed by discord.py
        # You can remove aiohttp if you don't use voice features
      ]))
    git
    postgresql
    gcc
  ];

  shellHook = ''
     echo "🔧 Nix Python dev shell activated"

     # Source the environment variables from your file
     if [ -f .env ]; then
       echo "Importing environment variables from .env..."
       source ./.env
       export DBPORT
       export DBADDRESS
       export DBPASSWORD
       export DBNAME
       export DBUSER
       export RABBIT_USER
       export RABBIT_PASSWORD
       export LOGLEVEL
       export discord_token
     else
       echo "No .env  file found. Continuing without extra environment variables."
     fi

     mkdir -p pip_target
    export PIP_TARGET=$(pwd)/pip_target
     export PYTHONPATH="$PIP_TARGET:$PYTHONPATH"
     echo "Installing pip-only packages..."
     which python

     pip install  \
       pandas_ta \
       ta \
       aiocron \
       mplfinance \
    aio_pika \
    numpy==1.26.0

     # Explicitly add gcc's lib directory to LD_LIBRARY_PATH
     export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH"
     echo "Set LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
     echo "✅ All packages ready"


  '';
}

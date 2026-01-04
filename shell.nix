{pkgs ? import <nixpkgs> {}}:
pkgs.mkShell {
  packages = with pkgs; [
    (python3.withPackages (ps:
      with ps; [
        aio-pika
        pip
        setuptools
        pandas
        pandas-ta
        numpy
        matplotlib
        mplfinance
        requests
        beautifulsoup4
        yfinance
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
    export SCAN
       export discord_token
     else
       echo "No .env  file found. Continuing without extra environment variables."
     fi

     echo "✅ All packages ready"


  '';
}

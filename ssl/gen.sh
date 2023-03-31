#/bin/bash
if [ -z $1 ]; then printf "\nSyntax: bash $0 [~/cert.cnf]\n\n"
else
CNF=$1
LOCATION="/opt/ssl"
if [ ! -d "$LOCATION" ]; then
	mkdir -p $LOCATION
fi
openssl req -config $CNF -newkey rsa -keyout $LOCATION/ghostwriter.key -x509 -days 365 -out $LOCATION/ghostwriter.crt
sudo chown -R root:docker $LOCATION
sudo chmod -R 644 $LOCATION
fi

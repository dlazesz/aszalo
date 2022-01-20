SHELL := /bin/bash -o pipefail
all: venv create

venv:
	virtualenv -p python3 venv
	./venv/bin/pip install sqlalchemy

create: ./venv/bin/pip mazsola_adatbazis.txt.zip
	@# Check integrity of input file and create database
	echo "e1f4be5f5652bfb32e85480bb6761a18c4ada32eb083062c3d50153d633cc48e mazsola_adatbazis.txt.zip" | \
	sha256sum -c - || exit 1
	export LC_ALL="C.UTF-8" && rm -rf mazsola_filtered_5.sqlite3 && \
	./venv/bin/python3 mazsola2sql.py -i mazsola_adatbazis.txt.zip -o mazsola_filtered_5.sqlite3 -f -t 5

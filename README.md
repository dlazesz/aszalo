
# Aszaló -- a general purpose search interface for annotated sentences inspired by Mazsola (Verb Argument Browser)

[Mazsola](https://github.com/sassbalint/mazsola)
([Verb Argument Browser](http://corpus.nytud.hu/mazsola/index_eng.html))
is a web application built upon the
[28 million syntactically analysed sentences and 500,000 verb structures](http://corpus.nytud.hu/isz)
data set.
The database is actually a TSV file (containing tabulated data) on which Mazsola uses the `grep` command
to serve queries that can be specified on the web interface.

The platform returns examples from the corpus for the selected features of verb argument structures
(e.g. the case fragment of the verb argument). The *radio buttons* on the interface can be used used to select a
criteria from the available feature set to classify the results according to it,
and further criteria can be used to specifically narrow the search.
The platform lists the results in order of importance (salience) according to the selected feature values.
This provides an oveview on the multitude of examples returned.

Aszaló generalizes the basic idea of Mazsola to modern technologies, other databases  and usage needs
(configurable field list, SQL database, JSON export, etc.).

# Features

- Ability to configure fields and set default values in the HTML form
- Permalink for each search
- Ability to handle sparse features by separate SQL tables
- JSON and TSV export of the query result (ready for machine/non-interactive usage)
- CLI frontend

# Setup

1. This software is tested on Python 3.10 on Linux
2. Install requirements from requirements.txt
3. Create config.yaml with the appropriate values (see [Configuration](#configuration) section) and create an [SQLite](https://www.sqlite.org/index.html) database
4. Run the application:
   - `app` class in `main.py` with an ASGI server like [uvicorn](https://www.uvicorn.org/) e.g. `uvicorn main:app`
   - Run `main.py` with CLI arguments

# Configuration

You are encouraged to create your really own database in Aszaló DB schema! :)

There are plenty of [example scripts](scripts), [configurations](example_configs) and [documentation](docs)
is provided to start with. Details on the configurations and advanced options can be found [here](docs/config.md).

In case of questions, feel free to ask!

# Examples

There are example configs and scripts bundled to be able to easily start, using the following databases:

- [PrevCons](https://github.com/kagnes/prevcons) created by Ágnes Kalivoda (the database is also bundled and the created demo service is available at: [https://aszalo.deta.dev/](https://aszalo.deta.dev/) )
- [Mazsola (Verb Argument Browser)](http://corpus.nytud.hu/mazsola/index_eng.html) created by Bálint Sass ([the database](http://corpus.nytud.hu/isz/) is too large to be included in this repository, but the conversion script is included in the [scripts](scripts) directory)

## Web UI usage examples

- The actual corpus forms for the `agyon` (lit. _to death_) preverb in HTML format: https://aszalo.deta.dev/?prev=agyon&sort=actform
- The actual corpus forms for the `agyon` preverb in TSV format: https://aszalo.deta.dev/?prev=agyon&sort=actform&format=TSV
- The actual corpus forms for the `agyon` preverb in JSON format: https://aszalo.deta.dev/?prev=agyon&sort=actform&format=JSON
- The actual corpus forms for the `agyon` preverb in HTML format, limited to the 30th-40th occurrence: https://aszalo.deta.dev/?prev=agyon&sort=actform&limit=10&page=2

## CLI usage examples

- The actual corpus forms for the `agyon` preverb in TSV format: `python3 main.py --prev agyon --sort actform`
- The actual corpus forms for the `agyon` preverb in JSON format: `python3 main.py --prev agyon --sort actform --format JSON`
- The actual corpus forms for the `agyon` preverb in HTML format, limited to the 30th-40th occurrence: `python3 main.py --prev agyon --sort actform --limit 10 --page 2`

# License

This project is licensed under the terms of the GNU LGPL 3.0 license.

# Acknowledgement

This software is inspired by but has no common part with [Mazsola](https://github.com/sassbalint/mazsola). The authors of this software would like to gratefully thank [Bálint Sass](http://github.com/sassbalint) and [Ágnes Kalivoda](http://github.com/kagnes) for their great databases which can be used in this software.
_Aszaló_ could not be created without the initial idea and implementation of Bálint Sass.

The authors created this software in the hope of encouraging researchers to create databases similar to the aforementioned ones, as these help the corpus linguist community to gain valuable insights into the data they are using.

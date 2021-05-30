
# Aszaló -- a general purpose search interface for annotated sentences inspired by Mazsola (Verb Argument Browser)

[Mazsola](https://github.com/sassbalint/mazsola) ([Verb Argument Browser](http://corpus.nytud.hu/mazsola/index_eng.html)) is a web frontend for investigating argument structure of verbs stored in flat files using `grep` as backend.
Aszaló generalizes this idea to modern technologies and usecases (configurable field list, SQL database, JSON export, etc.)

# Features

- Ability to configure fields and set default values in the HTML form
- Permalink for each search
- Ability to handle sparse features by separate SQL tables
- JSON and TSV export of the query result (ready for machine/non-interactive usage)
- CLI frontend

# Setup

1. This software is tested on Python 3.6 on Linux
2. Install requirements from requirements.txt
3. Create config.yaml with the appropriate values (see [Configuration](#configuration) section) and create an [SQLite](https://www.sqlite.org/index.html) database
4. Run the application:
   - `app` class in `main.py` with a WSGI server like [Gunicorn](https://gunicorn.org/) e.g. `gunicorn main:app --log-file=-`
   - Run `main.py` with CLI arguments

# Configuration

The configuration file is a YAML file restricted to the specific keys (validated by [YaMaLe](https://github.com/23andMe/Yamale)), which can be specified in _overlay style_ (values in default section is used for specific fields when missing) allowing to omit repeating default values.
The following sections can be specified:

## General configuration

- `title`: The title of the browser tab
- `database_name`: The path and name of the SQLite database (relative to `read_config.py`)
- `exluded_tables` (set): Tables to be exluded from the secondary field values (suggested value: main table if there are multiple tables)
- `exluded_columns` (set): Columns to be exluded from the primary field values at init time (suggested value: displayed_column_name value)
- `displayed_column_table_name`: The name of the table contains column to be displayed (usually sentences or clauses)
- `displayed_column_name`:  The name of the column to be displayed (usually sentences or clauses)
- `ui-strings`: The following fixed set of options for text shown on the search interface:
  - `locale`: The name of the locale to use for sorting
  - `submit`: The caption of the submit button
  - `reset`: The caption of the reset button (which resets form to the latest used setting)
  - `footer`: The HTML fragment to use for the footer (e.g. documentation, citation, etc.). In the `: ` (colon-space) substrings, space must be escaped with a `\` (slash) to avoid YAML parse error

## Form configuration

The `default` key contains the default values for each form element which can be overloaded in the specific field definitions. Each form element defined in `fields` as list element is displayed in the order of definition.
There are two types of fields: the _simple fields_ type has fixed table and column names, and displays the possible values as a scrollable _datalist_, while the _complex fields_ type has only the column fixed, and the user can specify the table to be used for the query in the secondary input field (_feature name_).
Eech field has one or two input fields and each has `not` and `regex` checkboxes which makes the query treat the corresponding input value as a negated value, a regular expression, or both.

The keys for each field element can be the following:

- `friendly_name`: The name to be used for referring to the field in the UI (field names in the HTML form and error messages)
- `table_name`: The database table name to be used for the field (if `null`, field is treated as _complex field_)
- `col_name`: The database column name to be used for the field
- `fn_value`: The default value for the _feature name_ if the field is complex
- `featelems_aliases`: The dictionary for additional aliases for SQL table names to be used in the form `alias: TABLE_NAME`
- `fn_not`: Boolean value to treat the secondary input value as negated or not
- `fn_regex`: Boolean value to treat the secondary input value as regex or not
- `api_name`: The name of the field in the API. The secondary field (feature name) is named `f{api_name}FEATNAME`, `not` and `regex` checkboxes are suffixed with `NOT` and `REGEX` automatically (e.g. `f{api_name}NOT`, f{api_name}REGEX` and `f{api_name}FEATNAME_NOT`, `f{api_name}FEATNAME_REGEX`)
- `value`: The default value for the primary input field
- `not`: Boolean value to treat the primary input value as negated or not
- `regex`: Boolean value to treat the primary input value as regex or not
- `sort_key`: Boolean value to treat the field as default sort key (exactly one key must be specified by setting this value true!)

## Other query parameters

These extra parameters can be used to modify the displayed results in the query:

- `format` (values can be 'HTML', 'TSV', 'JSON'): The output formats to display the results can be HTML, TSV and JSON according to the setting (the default is 'HTML' for WebUI and 'TSV' for the CLI)
- `limit` (default: 1000): The number of entries to be displayed (rounded up to completely display all entries for the last key)
- `page` (default: 0): The number of the page to be displayed in the paginated output

# Examples and bundled scripts

There are example configs and scripts bundled to be able to easily start, using the following databases:

- [PrevCons](https://github.com/kagnes/prevcons) created by Ágnes Kalivoda (the database is also bundled and the created demo service is available at: [https://aszalo.herokuapp.com/](https://aszalo.herokuapp.com/) )
- [Mazsola (Verb Argument Browser)](http://corpus.nytud.hu/mazsola/index_eng.html) created by Bálint Sass ([the database](http://corpus.nytud.hu/isz/) is too large to be included in this repository, but the conversion script is included in the [scripts](scripts) directory)

## WebUI usage examples

- The actual corpus forms for the `agyon` (lit. _to death_) preverb in HTML format: https://aszalo.herokuapp.com/?prev=agyon&sort=actform
- The actual corpus forms for the `agyon` preverb in TSV format: https://aszalo.herokuapp.com/?prev=agyon&sort=actform&format=TSV
- The actual corpus forms for the `agyon` preverb in JSON format: https://aszalo.herokuapp.com/?prev=agyon&sort=actform&format=JSON
- The actual corpus forms for the `agyon` preverb in HTML format limited to the 30th-40th occurence: https://aszalo.herokuapp.com/?prev=agyon&sort=actform&limit=10&page=2

## CLI usage examples

- The actual corpus forms for the `agyon` preverb in TSV format: `python3 main.py --prev agyon --sort actform`
- The actual corpus forms for the `agyon` preverb in JSON format: `python3 main.py --prev agyon --sort actform --format JSON`
- The actual corpus forms for the `agyon` preverb in HTML format limited to the 30th-40th occurence: `python3 main.py --prev agyon --sort actform --limit 10 --page 2`

# Licence

This project is licensed under the terms of the GNU LGPL 3.0 license.

# Acknowledgement

This software is inspired by but has no common part with [Mazsola](https://github.com/sassbalint/mazsola). The authors of this software would like to gratefully thank [Bálint Sass](http://github.com/sassbalint) and [Ágnes Kalivoda](http://github.com/kagnes) for their great databases which can be used in this software.
_Aszaló_ could not be created without the initial idea and implementation of Bálint Sass.

The authors created this software in the hope of encouraging researchers to create databases similar to the aforementioned ones, as these help the corpus linguist community to gain valuable insights into the data they are using.

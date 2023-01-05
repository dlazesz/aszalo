
# Aszaló -- a general purpose search interface for annotated sentences inspired by Mazsola (Verb Argument Browser)

[Mazsola](https://github.com/sassbalint/mazsola) ([Verb Argument Browser](http://corpus.nytud.hu/mazsola/index_eng.html)) is a web frontend for investigating argument structure of verbs stored in flat files using `grep` as backend.
Aszaló generalizes this idea to modern technologies and use cases (configurable field list, SQL database, JSON export, etc.)

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

The configuration file is a YAML file restricted to the specific keys (validated by [YaMaLe](https://github.com/23andMe/Yamale)), which can be specified in _overlay style_ (values in default section is used for specific fields when missing) allowing to omit repeating default values.
The following sections can be specified:

## General configuration

- `title`: The title of the browser tab
- `database_name`: The path and name of the SQLite database (relative to `read_config.py`)
- `excluded_tables` (set): Tables to be excluded from the secondary field values (suggested value: main table if there are multiple tables)
- `excluded_columns` (set): Columns to be excluded from the primary field values at init time (suggested value: displayed_column_name value and any column with very large distinct value set)
- `displayed_column_table_name`: The name of the table contains the column to be displayed (usually sentences or clauses)
- `displayed_column_name`:  The name of the column to be displayed (usually sentences or clauses)
- `ui-strings`: The following fixed set of options for text shown on the search interface:
  - `locale`: The name of the locale to use for sorting
  - `submit`: The caption of the submit button
  - `reset`: The caption of the reset button (which resets form to the latest used setting)
  - `clear_field_values`: The caption of the clear button (which clears values and checkboxes for all fields)
  - `footer`: The HTML fragment to use for the footer (e.g. documentation, citation, etc.). In the `: ` (colon-space) substrings, space must be escaped with a `\` (slash) to avoid YAML parse error
  - `n_more_elems`: The text fragment used to display in the select box if _N more elems available_ (`{0}` is used to denote the actual N)
  - `save_as_tsv` and `save_as_json`: The text of the link to save the result in the respective format

## Form configuration

The `default` key contains the default values for each form element, which can be overloaded in the specific field definitions. Each form element defined in `fields` as list element is displayed in the order of definition.
There are two types of fields: the _simple fields_ type has fixed table and column names, and displays the possible values as a scrollable _datalist_, while the _complex fields_ type has only the column fixed, and the user can specify the table to be used for the query in the secondary input field (_feature name_).
Each field has one or two input fields and each has `not` and `regex` checkboxes which makes the query treat the corresponding input value as a negated value, a regular expression, or both.

The keys for each field element can be the following:

- `friendly_name`: The name to be used for referring to the field in the UI (field names in the HTML form and error messages)
- `table_name`: The database table name to be used for the field (if `null`, field is treated as _complex field_)
- `col_name`: The database column name to be used for the field
- `fn_value`: The default value for the _feature name_ if the field is complex
- `featelems_aliases`: The dictionary for additional aliases for _feature name_ values (SQL table names) to be used in the form `alias: TABLE_NAME`
- `fn_not`: Boolean value to treat the secondary input value as negated or not
- `fn_regex`: Boolean value to treat the secondary input value as regex or not
- `api_name`: The name of the field in the API. The secondary field (feature name) is named `f{api_name}FEATNAME`, `not` and `regex` checkboxes are suffixed with `NOT` and `REGEX` automatically (e.g. `f{api_name}NOT`, `f{api_name}REGEX` and `f{api_name}FEATNAME_NOT`, `f{api_name}FEATNAME_REGEX`)
- `value`: The default value for the primary input field
- `not`: Boolean value to treat the primary input value as negated or not
- `regex`: Boolean value to treat the primary input value as regex or not
- `sort_key`: Boolean value to treat the field as default sort key (exactly one key must be specified by setting this value true!)
- `limit`: The upper limit for the number of displayed options in the dropdown list when typing (0 or greater, the displayed elems are in alphabetical order)
- `radio_tooltip`: Tooltip for the radio button
- `field_name_tooltip`: Tooltip for the field name text
- `not_tooltip`: Tooltip for the NOT text (for the first checkbox if there are two)
- `regex_tooltip`: Tooltip for the Regex text (for the first checkbox if there are two)
- `featname_not_tooltip`: Tooltip for the NOT text (for the second checkbox if there are two)
- `featname_regex_tooltip`: Tooltip for the Regex text (for the second checkbox if there are two)

## Other query parameters

These extra parameters can be used to modify the displayed results in the query:

- `format` (values can be `HTML`, `TSV`, `JSON`): The output formats to display the results can be HTML, TSV and JSON according to the setting (the default is 'HTML' for Web UI and 'TSV' for the CLI)
- `limit` (default: 1000): The number of entries to be displayed on one page (rounded up to completely display all entries for the last key)
- `page` (default: 0): The number of the page to be displayed in the paginated output

# Your really own database in Aszaló DB schema

1. Create a database in TSV format with a header for field names. If your data is sparse (e.g. verbal frames for grammatical cases) use NULL string for empty elements (and consider using separate tables in the database).
2. Create a configuration for [`tsv2sql.py`](scripts/tsv2sql.py)
3. Run [`tsv2sql.py -i your_database.TSV -o your_database.sqlite3 -c your_configuration.yaml`](scripts/tsv2sql.py)
4. Profit! :)

The configuration is similar to the one used in the [form configuration](#form-configuration) section. There is a default column which serves as an overlay for the omitted properties for the columns.
For each column, the following properties are required under the column key in a list:

- `column_name`: The name of the column in the input TSV
- `table_name`: Main table name (ignored for the actual column if it resides in separate table, e.g. separate is true)
- `sql_column_name`: Unified column name for separate tables or unique name for main table (ID as value is not allowed!)
- `column_type`: Type for SQL in Python format (`{'str', 'int', 'float', 'none'}` none means that the column is omitted from the database)
- `index`: Create index for column in the SQL or not (generally recommended to being set true, see 'general considerations')
- `separate`: Column belongs to the main table or to a separate table? (set/overwrite table_name if true)

The list of columns can be in arbitrary order, but must correspond to the TSV file column definitions.

Some general considerations:

- In the case of sparse data, it is advised to separate columns into different SQL tables (`separate: true`)
- It is advised to create index for columns which contain non-uniq elements and will be exposed to the frontend as it will make the queries faster, but makes the sqlite3 file larger (i.e. recommended for everything, but example sentences)
- Columns in the TSV can be omitted from the database if not used in the frontend (e.g. `column_type: none`)
- It is advised to use the proper type for the column, but be aware that using non-`str` type disables the regex option
- Try with small queries and generalize slowly, as queries can slow down fast if large amount of data needs to be considered

A [conversion script](scripts/mazsola2tsv.py) with [example configuration](scripts/mazsola_filtered_5.yaml) is provided for [Mazsola (Verb Argument Browser)](http://corpus.nytud.hu/mazsola/index_eng.html) as an example

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

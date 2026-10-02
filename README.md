# Any2MDF
Scripts for converting Excel and CSV files to MDF model files.

## Usage
python Any2MDF.py -c < path to config file > -v < verbosity.  Add more v's for more output >

## Config file fields
The configuration file must be in YAML format.  See the entires in the config directory for examples

| Field | Permissible Values | Notes |
|-------|--------------------|-------|
| source_sheet_type | xlsx, csv | The file format of the data model source information.  Currently only Excel and CSV files are supported |
| source_sheet_count | single, multi | Used mainly for Excel workbooks, how many tabs are used |
| source_sheet_delimiter | tab, comma | Only used for CSV source sheets |
| source_sheet_file | valid path | The full path to the source sheet |
| output_file_directory | valid path | Full path to a directory where you want the output files. |
| edp_enums | True, False | If True, both Term and Enum sections for Properties will be added.  False will create the deprecated Term-only Properties file. |
|-------|--------------------|-------|
| mappings | | Header for the next fivve fields that are used to describe where information lives in the source sheet |
| excluded_tabs | list of tab names | Any Excel spreadsheet tab listed here will be completely ignored by the program. |
| nodes | tab, or column name | If *tab*, the tab names will be used as node names.  Otherwise, should be the name of the column containing the node names |
| domains | column name | The name of the column containing domain names |
|-------|--------------------|-------|
| properties | | A sub-heading of mappings, and header for the next eight fields |
| property_name | 'None' or column name | The name of the column containing the property name |
| property_req |  'None' or column name | The name of the column indicating whether or not the property is a required property. |
| property_key |  'None' or column name | The name of the column indicating whether or not the property is a key property. |
| property_type |  'None' or column name | The name of the column indicating the type of data stored in a property. |
| property_description |  'None' or column name | The name of the column containing a description of a property. |
| cde_id |  'None' or column name | The name of the column containing the CDE identifier for the  property. |
| cde_version |  'None' or column name | The name of the column containing the CDE version for the  property. |
| cde_version |  'None' or column name | The name of the column containing the enumerated values for the  property. |
|-------|--------------------|-------|
|   edge_info | | A sub-heading of mappings and header for the next four fields |
| edge_info_source |  'None' or column name | The name of the workbook tab containing the relationship information. |
| edge_dst |  'None' or column name | The name of the column containing the destination node name. |
| edge_src |  'None' or column name | The name of the column containing the source node name. |
| edge_card |  'None' or column name | The name of the column containing the relationship cardinaltiy. |
|-------|--------------------|-------|
| model_info | | Header for the next two fields |
| handle | Text | The name for the model (example: CTDC, ICDC, SDM, etc.) |
| version | vX.Y.Z | The version number for the model, usually expressed as a lower-case "v" followed by a 3-digit nubmer in X.Y.Z format |
|-------|--------------------|-------|
| taginfo | | Header for the next two fields
| nodetags |  list of tag name: column name | For tagging Nodes.  The tag name should be the name of the tag as it appears in the MDF file.  The column should be the name of the column containing the value to be associated with the tag |
| propertytags | list of tag name: column name | For tagging Properties.  The tag name should be the name of the tag as it appears in the MDF file.  The column should be the name of the column containing the value to be associated with the tag |


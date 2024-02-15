import pandas as pd
import json
# import jsonld
import csv
import sys
import jsonschema
# from jsonschema import validate, ValidationError
import requests
from pyld import jsonld
import jsonref
from jsonpath_ng import jsonpath, parse
from datetime import datetime


# def remove_null_values(dictionary):
#   return {k: v for k, v in dictionary.items() if v is not None}

def _remove_null_values(dictionary):
    filtered = {k: v for k, v in dictionary.items() if v is not None and v != ''}
    dictionary.clear()
    dictionary.update(filtered)


def validate_context(jsld):
    """Validate a @context string through expanding"""
    context = jsld["@context"]
    # schema = jsld["credentialSchema"]
    # Validate the context
    try:
        jsonld.expand(context)
        print("Context is valid")
    except jsonld.JsonLdError:
        print("Context is not valid")
        return False
    return True


def compact_js(doc, context):
    """Validate a @context string through compacting, returns compacted context"""
    try:
        compacted = jsonld.compact(doc, context)
        print(json.dumps(compacted, indent=2))
    except jsonld.JsonLdError as e:
        print(f"Error compacting document: {e}")
        return None
    return compacted


def dereference_context_file(json_file):
    """Dereference and return json-ld context from file"""
    json_text = open(json_file).read()
    json_dict = json.loads(json_text)
    return dereference_context(json_dict)


def dereference_context(jsonld_dict):
    """Dereference and return json-ld context"""
    try:
        # Extract the context from the parsed JSON-LD
        context_urls = jsonld_dict.get('@context')
        if not context_urls:
            raise ValueError("No context found in the JSON-LD string.")
            return None

        # Dereference each context URL
        dereferenced_contexts = []
        for context_url in context_urls:
            response = requests.get(context_url)
            response.raise_for_status()  # Raise an exception if the request failed
            context_dict = response.json()
            dereferenced_context = jsonref.loads(json.dumps(context_dict))
            dereferenced_contexts.append(dereferenced_context)

        print(f"dereferenced contexts:\n", json.dumps(dereferenced_contexts, indent=4))
        return dereferenced_contexts

    except (json.JSONDecodeError, requests.RequestException, jsonref.JsonRefError) as e:
        print(f"An error occurred: {e}")
        return None


def validate_schema_file(json_schema_file):
    """Validate standalone schema from file"""
    try:
        json_schema = json.loads(open(json_schema_file).read())
        validate_schema(json_schema)
    except Exception as e:
        print(f"Error loading file {json_schema_file} or validating schema {json_schema}: {e}")
        return False
    return True


def validate_schema(json_schema):
    """Validate standalone schema, returns bool (uses Draft202012Validator, alt: Draft7Validator, alt: Draft4Validator, Draft6Validator )"""
    try:
        jsonschema.validators.Draft202012Validator.check_schema(json_schema)
        # jsonschema.validators.Draft7Validator.check_schema(json_schema)
    except jsonschema.exceptions.SchemaError as e:
        print(e)
        return False
    return True


def validate_json_file(json_data_file, json_schema_file):
    """Validate standalone schema from file"""
    try:
        json_data = json.loads(open(json_data_file).read())
        json_schema = json.loads(open(json_schema_file).read())
        validate_json(json_data, json_schema)
    except Exception as e:
        print(f"Error loading file {json_schema_file} or {json_data_file}: {e}")
        return False
    return True


def validate_json(json_data, json_schema):
    """Validate json string basic (no format) with schema, returns bool"""
    try:
        jsonschema.validate(instance=json_data, schema=json_schema)
    except jsonschema.exceptions.ValidationError as err:
        print('Validation error: ', json_data, '\n')
        return False
    print("Successful validation")
    return True


def validate_json_format(json_data, json_schema):
    """Validate a json string basic (including format) with schema, returns bool"""
    try:
        jsonschema.validate(instance=json_data, schema=json_schema, format_checker=FormatChecker())
    except jsonschema.exceptions.ValidationError as err:
        print('Validation error: ', json_data, '\n')
        return False
    return True


def schema_to_csv_file(sch_f, csv_f):
    try:
        json_schema = json.loads(open(sch_f).read())
    except Exception as e:
        print(f"Error loading file {sch_f}: {e}\nSchema:\n{json_schema}.")
        return False
    schema_to_csv(json_schema, csv_f)
    return True


def schema_to_csv(schema, csv_file_path):
    """Extract headers from an schema and write to file, returns bool"""
    jsonpath_expr = parse('$..credentialSubject.properties')
    # Use the JSONPath expression to select all properties under 'credentialSubject.properties'
    matches = [match.value for match in jsonpath_expr.find(schema)]
    # Get the keys of the matched objects
    # headers = [match.keys() for match in matches]
    # Use the JSONPath expression to select all properties under 'credentialSubject.properties'

    # Get the keys of the matched objects
    headers = [key for match in matches for key in match.keys()]
    # print('\nHeaders: ', headers)

    # Create a CSV file with the headers
    with open(csv_file_path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
    return True

def schema_to_xls_basic(schema, xls_file_path):
  """Extract headers from an schema and write to file, returns bool"""
  jsonpath_expr = parse('$..credentialSubject.properties')
  # Use the JSONPath expression to select all properties under 'credentialSubject.properties'
  matches = [match.value for match in jsonpath_expr.find(schema)]
  # Get the keys of the matched objects
  # headers = [match.keys() for match in matches]
  
  # Get the keys of the matched objects
  headers = [key for match in matches for key in match.keys() if key != 'id']
  
  # Create a DataFrame with the fields as columns
  df = pd.DataFrame(columns=headers)

  # Save the DataFrame as an Excel file
  # df.to_excel(xls_file_path, index=False)
  df.to_excel(xls_file_path, index=False, engine='openpyxl') # For .xlsx files, and pip install openpyxl
  return True

def schema_to_xls_comment(schema, xls_file_path):
  """Extract headers from an schema and write to file, returns bool"""
  jsonpath_expr = parse('$..credentialSubject.properties')
  # Use the JSONPath expression to select all properties under 'credentialSubject.properties'
  matches = [match.value for match in jsonpath_expr.find(schema)]
  # Get the keys of the matched objects
  # headers = [match.keys() for match in matches]
  
  # Get the keys of the matched objects
  headers = [key for match in matches for key in match.keys() if key != 'id']

  jsonpath_expr_req = parse('$..credentialSubject.required')
  req = [match.value for match in jsonpath_expr_req.find(schema)][0]

  # Create a DataFrame with the fields as columns
  df = pd.DataFrame(columns=headers)
  
  writer = pd.ExcelWriter(xls_file_path, engine='xlsxwriter')

  # Convert the dataframe to an xlsxwriter Excel object
  df.to_excel(writer, sheet_name='Full1', index=False)

  # Get the xlsxwriter workbook and worksheet objects
  workbook = writer.book
  
  matches_title = parse('$.title').find(schema)
  title = matches_title[0].value if matches_title else 'no title'

  matches_desc = parse('$.description').find(schema)
  desc = matches_desc[0].value if matches_desc else 'no description'
  
  matches_id = parse("$['$id']").find(schema)
  idschema = matches_id[0].value if matches_id else 'no schema'
  
  matches_subject_desc = parse('$..credentialSubject.description').find(schema)
  subject_desc = matches_subject_desc[0].value if matches_subject_desc else 'no subject description'
  
  workbook.set_properties({
    'title':    title,
    'subject':  desc,
    'author':   'IdHub Orchestral',
    'category': subject_desc,
    'keywords': 'schema, template, plantilla',
    'created':  datetime.now().date(), #datetime.date(2018, 1, 1),
    'comments': 'Created with Python for IdHub'})

  workbook.set_custom_property('Schema', idschema)
 
  worksheet = writer.sheets['Full1']

  # Define a format for the required header cells
  req_f = workbook.add_format({'border': 1})
  req_da = workbook.add_format({'border': 1, 'num_format': 'yyyy-mm-dd'})
  req_in = workbook.add_format({'border': 1, 'num_format': '0'})
  req_st = workbook.add_format({'border': 1, 'num_format': '@'})
  opt_da = workbook.add_format({'num_format': 'yyyy-mm-dd'})
  opt_in = workbook.add_format({'num_format': '0'})
  opt_st = workbook.add_format({'num_format': '@'})
  fmts = {
    'string' : {True: req_st, False: opt_st},
    'date' : {True: req_da, False: opt_da},
    'integer' : {True: req_in, False: opt_in}
  }

  # Write comments to the cells
  for i, header in enumerate(headers):
    fmt = {}
    #if header in req:
    #    fmt = req_format
    # worksheet.set_column(i,i, None, req_format)
   
    # Get the description for the current field
    if 'description' in matches[0][header]:
      description = matches[0][header]['description']
      if description is not None:
        # Write the description as a comment to the corresponding cell
        worksheet.write_comment(0, i, description)
   
    # Get the type for the current field
    if 'type' in matches[0][header]:
      type_field = matches[0][header]['type']

      format_field = None
      if 'format' in matches[0][header]:
        format_field = matches[0][header]['format']
      
      if type_field is not None:
        if format_field is not None and format_field == 'date':
            type_field = 'date'
        fmt = fmts[type_field][header in req] # Add type format

    print(f'header {header} with fmt {fmt}\n')
    worksheet.set_column(i,i, None, fmt)    
        
  # Close the Pandas Excel writer and output the Excel file
  worksheet.autofit()
  writer.close()
  return True

def csv_to_json(csvFilePath, schema, jsonFilePath):
    """Read from a csv file, check schema, write to json file, returns bool"""
    jsonArray = []
    # Read CSV file
    with open(csvFilePath, 'r') as csvf:
        # Load CSV file data using csv library's dictionary reader
        csvReader = csv.DictReader(csvf)

        # Convert each CSV row into python dict and validate against schema
        for row in csvReader:
            _remove_null_values(row)
            print('Row: ', row, '\n')
            validate_json(row, schema)
            # Add this python dict to json array
            jsonArray.append(row)

    # Convert python jsonArray to JSON String and write to file
    with open(jsonFilePath, 'w', encoding='utf-8') as jsonf:
        jsonString = json.dumps(jsonArray, indent=4)
        jsonf.write(jsonString)
    return True


def csv_to_json2(csv_file_path, json_file_path):
    """Read from a csv file, write to json file (assumes a row 'No' is primary key), returns bool EXPERIMENT"""
    # Create a dictionary
    data = {}

    # Open a csv reader called DictReader
    with open(csv_file_path, encoding='utf-8') as csvf:
        csvReader = csv.DictReader(csvf)

        # Convert each row into a dictionary and add it to data
        for rows in csvReader:
            # Assuming a column named 'No' to be the primary key
            key = rows['No']
            data[key] = rows

    # Open a json writer, and use the json.dumps() function to dump data
    with open(json_file_path, 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(data, indent=4))
    return True


if __name__ == "__main__":
   # sch_name = sys.argv[1]
   schemas = sys.argv[1:]
   
   # credtools.py course-credential device-purchase e-operator-claim federation-membership financial-vulnerability membership-card
   #sch_name = 'e-operator-claim'
   
   for i, schema in enumerate(schemas):
     print(schema)
     sch = json.loads(open('vc_schemas/' + schema + '.json').read())
     if schema_to_xls_comment(sch,'vc_excel/' + schema + '.xlsx'):
       print('Success')
     else:
       print("Validation error: ", schema)

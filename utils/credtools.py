import json
#import jsonld
import csv
import sys
import jsonschema
from pyld import jsonld
#from jsonschema import validate, ValidationError
import requests
from pyld import jsonld
import jsonref

#def remove_null_values(dictionary):
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
          response.raise_for_status() # Raise an exception if the request failed
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
    json_schema = open(json_schema_file).read()
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
      return True
   except jsonschema.exceptions.SchemaError as e:
       print(e)
       return False

def validate_json(json_data, json_schema):
   """Validate json string basic (no format) with schema, returns bool"""
   try:
       jsonschema.validate(instance=json_data, schema=json_schema)
   except jsonschema.exceptions.ValidationError as err:
       print('Validation error: ', json_data, '\n')
       return False
   return True

def validate_json_format(json_data, json_schema):
   """Validate a json string basic (including format) with schema, returns bool"""
   try:
       jsonschema.validate(instance=json_data, schema=json_schema, format_checker=FormatChecker())
   except jsonschema.exceptions.ValidationError as err:
       print('Validation error: ', json_data, '\n')
       return False
   return True

def schema_to_csv(schema, csv_file_path):
   """Extract headers from an schema and write to file, returns bool"""
   headers = list(schema['properties'].keys())

   # Create a CSV file with the headers
   with open(csv_file_path, 'w', newline='') as csv_file:
      writer = csv.writer(csv_file)
      writer.writerow(headers)
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
   sch_name = sys.argv[1]
   sch_file = sch_name + '-schema.json'
   sch = json.loads(open(sch_file).read())
   if validate_json(d, sch):
     generate_csv_from_schema(sch, sch_name + '-template.csv')
   else:
     print("Validation error: ", sch_name)
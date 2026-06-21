from google import generativeai
import torch
import json
import requests
import ast
import re
import os
from dotenv import load_dotenv

load_dotenv()


def clean_ai_output(response_text):
   
    cleaned = re.sub(r"```(?:python|json)?", "", response_text).strip()
    
    try:
        if cleaned != 'finished':
            data_dict = json.loads(cleaned)
            return data_dict
    except json.JSONDecodeError:
        return cleaned
    

def safe_convert(value):

    if isinstance(value, str):
        try:
            
            return ast.literal_eval(value)
        except (ValueError, SyntaxError, TypeError):
            
            if value.startswith("tensor(") and value.endswith(")"):
                inner = value[len("tensor("):-1].strip()  
                try:
                    data = ast.literal_eval(inner)  
                    return torch.tensor(data)
                except Exception:
                    return value  
            return value
    else:
        return value   
    

def database():
            
    return {
    "functions": {
        "run_sql_query": {
            "role": "Database query",
            "description": "Executes a SQL query against a database using SQLAlchemy and returns the result as a Pandas DataFrame.",
            "args": {
                "connection_string": {
                    "type": "str",
                    "description": "A valid SQLAlchemy connection string (e.g., 'postgresql://user:pass@host:5432/db')."
                },
                "query": {
                    "type": "str",
                    "description": "SQL query to execute."
                }
            },
            "arg_count": 2,
            "return_type": "pd.DataFrame",
            "example": "run_sql_query('postgresql://user:pass@localhost:5432/mydb', 'SELECT * FROM sales;')"
        },
        "load_csv_from_s3": {
            "role": "Data loading",
            "description": "Loads a CSV file from an AWS S3 bucket into a Pandas DataFrame.",
            "args": {
                "bucket": {"type": "str", "description": "S3 bucket name."},
                "key": {"type": "str", "description": "Key (path) to the CSV file in the bucket."},
                "separator": {"type": "str", "description": "CSV delimiter (default ',')."}
            },
            "arg_count": 3,
            "return_type": "pd.DataFrame",
            "example": "load_csv_from_s3('my-bucket', 'data/sales.csv', ',')"
        },
        "handle_missing_values": {
            "role": "Data cleaning",
            "description": "Handles missing values in a specified column using strategies like 'drop', 'fill', 'mean', 'median'.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "column": {"type": "str", "description": "Column to clean."},
                "strategy": {"type": "str", "description": "Strategy for handling missing values."},
                "fill_value": {"type": "any", "description": "Fill value if strategy='fill'."}
            },
            "arg_count": 4,
            "return_type": "pd.DataFrame",
            "example": "handle_missing_values(df, 'price', 'mean')"
        },
        "remove_duplicates": {
            "role": "Data cleaning",
            "description": "Removes duplicate rows from a DataFrame.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."}
            },
            "arg_count": 1,
            "return_type": "pd.DataFrame",
            "example": "remove_duplicates(df)"
        },
        "change_column_type": {
            "role": "Data transformation",
            "description": "Converts the data type of a column to integer, float, string, or datetime.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "column": {"type": "str", "description": "Column to convert."},
                "new_type": {"type": "str", "description": "Target type: 'integer', 'float', 'string', 'datetime'."}
            },
            "arg_count": 3,
            "return_type": "pd.DataFrame",
            "example": "change_column_type(df, 'date', 'datetime')"
        },
        "rename_columns": {
            "role": "Data transformation",
            "description": "Renames one or more columns in a DataFrame.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "rename_map": {"type": "dict", "description": "Mapping of old to new column names."}
            },
            "arg_count": 2,
            "return_type": "pd.DataFrame",
            "example": "rename_columns(df, {'old': 'new'})"
        },
        "filter_rows": {
            "role": "Data filtering",
            "description": "Filters rows in a DataFrame based on a condition.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "column": {"type": "str", "description": "Column to filter."},
                "operator": {"type": "str", "description": "Operator (==, !=, >, <, >=, <=, contains)."},
                "value": {"type": "any", "description": "Value for comparison."}
            },
            "arg_count": 4,
            "return_type": "pd.DataFrame",
            "example": "filter_rows(df, 'price', '>', 100)"
        },
        "select_columns": {
            "role": "Data selection",
            "description": "Keeps only the specified columns in the DataFrame.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "columns_to_keep": {"type": "list", "description": "List of columns to retain."}
            },
            "arg_count": 2,
            "return_type": "pd.DataFrame",
            "example": "select_columns(df, ['id', 'price'])"
        },
        "join_dataframes": {
            "role": "Data merging",
            "description": "Joins two DataFrames on a common column using inner, left, right, or outer join.",
            "args": {
                "df1": {"type": "pd.DataFrame", "description": "First DataFrame."},
                "df2": {"type": "pd.DataFrame", "description": "Second DataFrame."},
                "on_column": {"type": "str", "description": "Join key column."},
                "how": {"type": "str", "description": "Join type (default 'inner')."}
            },
            "arg_count": 4,
            "return_type": "pd.DataFrame",
            "example": "join_dataframes(df1, df2, 'id', 'left')"
        },
        "group_by_aggregate": {
            "role": "Data aggregation",
            "description": "Groups a DataFrame by a column and aggregates another column with sum, mean, count, std, min, or max.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "group_by_col": {"type": "str", "description": "Column to group by."},
                "agg_col": {"type": "str", "description": "Column to aggregate."},
                "agg_func": {"type": "str", "description": "Aggregation function."}
            },
            "arg_count": 4,
            "return_type": "pd.DataFrame",
            "example": "group_by_aggregate(df, 'category', 'sales', 'sum')"
        },
        "sort_values": {
            "role": "Data sorting",
            "description": "Sorts a DataFrame by a column.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "by_column": {"type": "str", "description": "Column to sort by."},
                "ascending": {"type": "bool", "description": "Sort ascending (default False)."}
            },
            "arg_count": 3,
            "return_type": "pd.DataFrame",
            "example": "sort_values(df, 'sales', ascending=True)"
        },
        "get_descriptive_statistics": {
            "role": "Data analysis",
            "description": "Calculates descriptive statistics (mean, median, std, min, max, count) for a numeric column.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "column": {"type": "str", "description": "Numeric column for stats."}
            },
            "arg_count": 2,
            "return_type": "dict",
            "example": "get_descriptive_statistics(df, 'price')"
        },
        "display_stats": {
            "role": "Data visualization / reporting",
            "description": "Displays the contents of a descriptive statistics dictionary in a readable format, with an optional title.",
            "args": {
                "stats": {"type": "dict", "description": "Dictionary containing descriptive statistics."},
                "title": {"type": "str", "description": "Optional title to display above the statistics."}
            },
            "arg_count": 2,
            "return_type": "None (prints statistics to console)",
            "example": "display_stats(stats, title='Daily Sales Statistics')"
        },
        "display_head": {
            "role": "Data inspection",
            "description": "Displays the first N rows of a DataFrame for inspection.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "n": {"type": "int", "description": "Number of rows to display."}
            },
            "arg_count": 2,
            "return_type": "pd.DataFrame",
            "example": "display_head(df, 5)"
        },
        "plot_bar_chart": {
            "role": "Data visualization",
            "description": "Plots a bar chart from the DataFrame.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "x_col": {"type": "str", "description": "X-axis column."},
                "y_col": {"type": "str", "description": "Y-axis column."},
                "title": {"type": "str", "description": "Chart title."}
            },
            "arg_count": 4,
            "return_type": "None (displays chart)",
            "example": "plot_bar_chart(df, 'category', 'sales', 'Sales by Category')"
        },
        "plot_line_chart": {
            "role": "Data visualization",
            "description": "Plots a line chart from the DataFrame, ideal for time-series data.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "Input DataFrame."},
                "x_col": {"type": "str", "description": "X-axis column."},
                "y_col": {"type": "str", "description": "Y-axis column."},
                "title": {"type": "str", "description": "Chart title."}
            },
            "arg_count": 4,
            "return_type": "None (displays chart)",
            "example": "plot_line_chart(df, 'date', 'daily_sales', 'Daily Sales Trend')"
        },
        "save_dataframe_to_csv": {
            "role": "Data export",
            "description": "Saves a DataFrame to a local CSV file.",
            "args": {
                "dataframe": {"type": "pd.DataFrame", "description": "DataFrame to save."},
                "filename": {"type": "str", "description": "File path/name for CSV."}
            },
            "arg_count": 2,
            "return_type": "None (saves file)",
            "example": "save_dataframe_to_csv(df, 'output.csv')"
        }
    },
    "instruction_version": "1.1"
}



class Controller:
        def __init__(self,start,api_key, gemini_key, function_registry=None, header_row=None):
            self.check = self.valid_apitoken(api_key)
            if self.check:   
                self.store = {}
                self.repsonse = {}
                self.slow_save = []
                self.api_key = api_key
                self.start = start
                self.function_registry = function_registry
                self.header_row = header_row
                generativeai.configure(api_key=gemini_key)
                self.model = generativeai.GenerativeModel('gemini-3.5-flash')
                self.function_response = start
                self.instruction = None
                self.connect_database()
                self.chat = self.model.start_chat()  
                if self.instruction:
                    self.trigger(self.instruction)  
                    self.run()   
            else:
                raise PermissionError("Invalid API token")
            
            
        def connect_database(self): 
            headers = {"Authorization": f"token {self.api_key}"}
            response = requests.get("https://agentic-ai-nt21.onrender.com/connect",headers=headers)
            response = response.json()  
            self.instruction = response


        def valid_apitoken(self,api_key):
            headers = {"Authorization": f"token {api_key}"}
            response = requests.get("https://agentic-ai-nt21.onrender.com/valid",headers=headers)
            return response.json()['result']
        

        def _instruction_watcher(self):
            if self.instruction:
                self.trigger(self.instruction)  
                self.run()  
                

        def trigger(self,instruction):

            prompt = f"""
            You are Gemini, the brain controlling multiple AI agents.
            The prebuilt functions are: "{instruction}".
            The available user functions are: "{self.function_registry}".
            The query to process is: "{self.start}".
            The dataframe headers are: "{self.header_row}".

            Instructions:
            1. Analyze the instruction and query.
            2. Determine the functions to executed.
            3. Extract necessary arguments.
            4. Return the result strictly as a valid Python dictionary — no additional text, explanations, or formatting other than the dictionary itself.
            5. Use the literal string 'df' for the dataframe argument, but change or create a new DataFrame if required..
            6. If argument requires the previous function output, just pass the name of the function as argument value.
            7. If all instructions are completely processed, respond with the string: "finished".

            Constraint:
            - Output MUST be valid JSON.
            - Do NOT wrap in markdown code blocks like ```json.

            Always return your response in the following valid JSON format:
            [
            {{
                "arguments": {{ "<arg_name>": <arg_value> or <previous_function>, ... }},
                "function": "name of the function in which argument has to be passed"
            }},
            ]

            """
            self.slow_save.append(prompt)
            print("output: 'yes I understand the instructions'")

            
        def run(self):
        
            prompt = f"""
            You are continuing from a previous interaction.  
            The previous interactions are recorded in the list: {str(self.slow_save)}
            (Note: The index of the list represents the timeline/order of each event.)  

            Instructions:
            - Do not add any explanation or code.
            - Return only a Python dictionary (no comments or text).
            - Do NOT use markdown formatting like ```json.
            - Output must start directly with and be valid for json.loads().
            """

            response = self.chat.send_message(prompt)
            cleaned_response = clean_ai_output(response.text)
            
            
            if isinstance(cleaned_response, list):
                self.response = cleaned_response
            elif isinstance(cleaned_response, dict):
                 
                 self.response = [cleaned_response]
            else:
                 
                 print("Error: LLM did not return a list or dict.", cleaned_response)
                 self.response = []

            for step in self.response:
                if isinstance(step, dict):
                    
                    for key, value in step.get('arguments', {}).items():  
                        step['arguments'][key] = safe_convert(value)
            
            print("Convertor Response:", self.response) 

            if self.response:
                self.slow_save.extend(self.response)

        def get_output(self):
            self.slow_save.pop(0)
            return self.slow_save



def creator(start,save_id, gemini_key, function_registry=None, header_row=None):    
    return Controller(start,save_id, gemini_key, function_registry, header_row)    


          
           
         
            
            

                    
                   

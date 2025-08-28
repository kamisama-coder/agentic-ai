from google import genai,generativeai
import threading
import importlib.util
import torch
import json
import requests
import ast
import re
import os

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
            # First try normal literal evaluation
            return ast.literal_eval(value)
        except (ValueError, SyntaxError, TypeError):
            # Handle torch tensor strings like "tensor([1.0, 2.0, 3.0])"
            if value.startswith("tensor(") and value.endswith(")"):
                inner = value[len("tensor("):-1].strip()  # extract inside part
                try:
                    data = ast.literal_eval(inner)  # parse safely into list/tuple
                    return torch.tensor(data)
                except Exception:
                    return value  # fallback to original string
            return value
    else:
        return value   


class Controller:
        def __init__(self,start,api_key,filename,type):
            self.check = self.valid_apitoken(api_key)
            if self.check:   
                spec = importlib.util.spec_from_file_location("file1",filename)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                self.type = type
                self.module_dict = vars(module)
                self.store = {}
                self.repsonse = {}
                self.slow_save = []
                self.api_key = api_key
                self.start = start
                generativeai.configure(api_key='AIzaSyADvZjtVNSnOAnNUGJcMB1oWiC3ZgwAhFY')
                self.model = generativeai.GenerativeModel('gemini-2.5-flash')
                self.function_response = start
                self.instruction = None
                self.decrease_token()
                self.connect_database()
                self.chat = self.model.start_chat()
                # self.thread = threading.Thread(target=self._instruction_watcher, daemon=True)
                # self.thread.start()      
                if self.instruction:
                    self.trigger(self.instruction)  
                    self.run()   
            else:
                raise PermissionError("Invalid API token")
            

        def decrease_token(self):
            headers = {"Authorization": f"token {self.api_key}"}
            requests.get("http://localhost:8000/decrease_token",headers=headers)
            


        def connect_database(self):
            headers = {"Authorization": f"token {self.api_key}"}
            response = requests.get("http://localhost:8000/connect",headers=headers)
            self.instruction = response.json()
            print(self.instruction)
#             self.instruction = {
#     "functions": {
#         "part1": {
#             "role": "LLM task",
#             "description": "Send a prompt to the Google Generative AI (Gemini) model and return a text response.",
#             "args": {
#                 "prompt": {
#                     "type": "str",
#                     "description": "The natural language prompt to send to the LLM."
#                 }
#             },
#             "arg_count": 1,
#             "return_type": "str",
#             "example": 'part1("Write a poem about the ocean.")'
#         },
#         "get_text_embedding": {
#             "role": "Text embedding",
#             "description": "Encodes input text into a normalized CLIP embedding vector.",
#             "args": {
#                 "statement": {
#                     "type": "str",
#                     "description": "The input text to convert into embeddings."
#                 }
#             },
#             "arg_count": 1,
#             "return_type": "torch.Tensor (1, hidden_dim)",
#             "example": 'get_text_embedding("A cat sitting on a sofa.")'
#         },
#         "get_image_embedding": {
#             "role": "Image embedding",
#             "description": "Encodes an image into a normalized CLIP embedding vector.",
#             "args": {
#                 "image_path": {
#                     "type": "str",
#                     "description": "Path to the image file (e.g., .jpg or .png)."
#                 }
#             },
#             "arg_count": 1,
#             "return_type": "torch.Tensor (1, hidden_dim)",
#             "example": 'get_image_embedding(r"C:/Users/ASUS/Downloads/saas/app/chinese vase.jpg")'
#         },
#         "cosine_similarity": {
#             "role": "Similarity scoring",
#             "description": "Computes cosine similarity between two embeddings.",
#             "args": {
#                 "embedding1": {
#                     "type": "torch.Tensor",
#                     "description": "First embedding (e.g., text)."
#                 },
#                 "embedding2": {
#                     "type": "torch.Tensor",
#                     "description": "Second embedding (e.g., image)."
#                 }
#             },
#             "arg_count": 2,
#             "return_type": "float",
#             "example": "cosine_similarity(text_emb, img_emb)"
#         }
#     },
#     "instruction_version": "1.1"
# }

        def valid_apitoken(self,api_key):
            headers = {"Authorization": f"token {api_key}"}
            response = requests.get("http://localhost:8000/valid",headers=headers)
            return response.json()['result']
        

        def _instruction_watcher(self):
            if self.instruction:
                self.trigger(self.instruction)  
                self.run()  

        def trigger(self,instruction):
            prompt = f"""
            You are Gemini, the brain controlling multiple AI agents.
            The user will provide the following instruction to be processed: "{instruction}".
            The query to process is "{self.start}".

            For each cycle:
            1. Process the provided input according to the instruction.
            2. If applicable, extract arguments or additional parameters from the input.
            3. Determine the appropriate next function or AI agent to handle the processed data.
            4. Pass the processed input to that function or agent.
            5. Continue this process until the entire flow of instructions is completed.
            6. Return the result strictly as a valid Python dictionary — no additional text, no explanations, no formatting other than the dictionary itself.

            Always return your response in the following dictionary format:
            {{
                "output": "<processed input or transformed data>",
                "arguments": {{ "<arg_name>": <arg_value>, ... }},
                "function": "name of the function in which argument has to be passed"
            }}

            """
            self.slow_save.append(prompt)
            print("output: 'yes I understand the instructions'")

            
        def run(self):
         check = {}

         while True:

            prompt = f"""
           You are continuing from a previous interaction.  
            The previous interactions are recorded in the list: {str(self.slow_save)}
            (Note: The index of the list represents the timeline/order of each event.)  

            Instructions:
            - Do not add any explanation or code.
            - Return only a Python dictionary (no comments or text).
            - Do NOT use markdown formatting like ```json.
            - Output must start directly with and be valid for json.loads().
            - Now, in the previous interaction, each function had a return part. Please use them accordingly.
            - do not change the return type.I repeat do not change the return type when passing throgh argument
            """

            response = self.chat.send_message(prompt)

            self.response = clean_ai_output(response.text)
            if response.text == 'finished':
                    print(self.response['output'])
                    break

            for key,value in self.response['arguments'].items():
                print(type(self.response))
                self.response['arguments'][key] = safe_convert(value)

            print("Convertor Response:", self.response) 

            try:
                recieved_imf = self.module_dict[self.response['function']](**self.response['arguments'])
                check['function_returned_part'] = recieved_imf
                check['function'] = self.response['function']
                check['return type'] = type(recieved_imf)
                self.slow_save.append(check)

            except (KeyError,TypeError,AttributeError):                                                                          
                self.response['output'] = safe_convert(self.response['output'])
                if not isinstance(self.response['output'], self.type):
                    self.function_response = self.start
                    self.slow_save = []
                    continue

                print(self.response['output'])    
                break




def creator(start,save_id,filename,type):    
    return Controller(start,save_id,filename,type)       
            
current_dir = os.path.dirname(os.path.abspath(__file__))

filename = os.path.join(current_dir, "test.py")


creation_obj = creator(
    "generate a sentence about a 'vase' and generate the embeddings of the text and generate the embeddings of the image 'chinese vase.jpg' and compare them",
    '426c9a80311faad2398f28032b975c04183d324ef2afa0b29ba233ee56b1042b',
    filename,
    float
)            

            
            
            

                    
                   

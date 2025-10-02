import requests
import inspect
import json
import app.test

functions = {
    name: inspect.getsource(obj)
    for name, obj in inspect.getmembers(app.test, inspect.isfunction)
}

import_lines = [
    "from google import genai, generativeai",
    "import json",
    "import torch",
    "from PIL import Image",
    "import clip",
    "import os"
]

functions = json.dumps(functions)
print(functions)

params = {
    "prompt": "generate a sentence about a 'vase' and generate the embeddings of the text and generate the embeddings of the image 'chinese vase.jpg' and compare them",
    "return_type": "float",
    "filepy": functions,
    "import_lines": import_lines
}


headers = {"Authorization": "token aa47fcb7de42ea818c32fb81f8087089faad90d13de7b5fe4cce2be0ae820ae7"}

response = requests.post("http://localhost:8000/call",json=params,headers=headers)
print("Status:", response.status_code)
print("Response:", response.json())
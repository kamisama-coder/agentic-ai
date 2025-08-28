from google import genai, generativeai
import json
import torch
from PIL import Image
import clip
import os



def get_clip_model():
    import clip
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)
    return model, preprocess, device



def part1(prompt):
    """
    Send prompt to GenAI model and get response
    """
    client = genai.Client(api_key='AIzaSyADvZjtVNSnOAnNUGJcMB1oWiC3ZgwAhFY')
    raw_response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return raw_response.text


def get_text_embedding(statement):
    """
    Encode text using CLIP model and return features as list
    """
    model, preprocess, device = get_clip_model()
    text = clip.tokenize(statement).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text)
    return text_features / text_features.norm(dim=-1, keepdim=True) 


def get_image_embedding(image_path):
    model, preprocess, device = get_clip_model()
    image = preprocess(Image.open(r"C:\Users\ASUS\Downloads\saas\app\chinese vase.jpg")).unsqueeze(0).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image)
    return image_features / image_features.norm(dim=-1, keepdim=True)  


def cosine_similarity(embedding1, embedding2):
    return (embedding1 @ embedding2.T).item()

   
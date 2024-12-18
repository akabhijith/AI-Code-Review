from celery import Celery
import os
import requests
from redis import Redis
from typing import Optional
from openai import OpenAI
from langchain_community.llms import Ollama
celery_app = Celery(
    'app',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)
redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
GITHUB_API_URL = "https://api.github.com"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_api_key = OPENAI_API_KEY

def analyze_code_with_openai(file_name, content):
    client = OpenAI(api_key=openai_api_key)
    prompt = f"Analyze the following code and provide feedback on style issues, potential bugs, and best practices:\n\n{content}"
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def analyze_code_with_ollama(file_name, content):
    llm = Ollama(model="codellama:7b")
    prompt = f"Analyze the following code and provide feedback on style issues, potential bugs, and best practices:\n\n{content}"
    return llm.invoke(prompt)

@celery_app.task(bind=True)
def analyze_pr_task(self,repo_url, pr_number, github_token):
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    try:
        repo_path = repo_url.rstrip("/").replace("https://github.com/", "")
        pr_api_url = f"{GITHUB_API_URL}/repos/{repo_path}/pulls/{pr_number}/files"

        response = requests.get(pr_api_url, headers=headers)
        response.raise_for_status()
        files = response.json()

        if not files:
            return {"status": "error", "message": "No files found in the pull request."}


        #Download file contents
        # Download the contents of each file
        analysis_results = {}
        for file in files:
            file_url = file.get("raw_url")
            file_name = file.get("filename")
            if file_url and file_name:
                file_response = requests.get(file_url, headers=headers)
                file_response.raise_for_status()
                content = file_response.text

                # Analyze the code using the selected AI model
                if openai_api_key:
                    analysis = analyze_code_with_openai(file_name, content)
                else:
                    analysis = analyze_code_with_ollama(file_name, content)

                analysis_results[file_name] = analysis

        return {"status": "success", "results": analysis_results}

    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

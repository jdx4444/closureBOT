import openai

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read().strip()  # strip to remove any trailing whitespace or newline
    
def save_file(filepath, content):
    with open(filepath, 'a', encoding='utf-8') as outfile:
        outfile.write(content)

# (Replace 'YOUR_API_KEY_HERE' with your actual API key)
openai.api_key = "YOUR_API_KEY_HERE"

file_id = "YOUR FILE ID"
model_name = "gpt-3.5-turbo"

response = openai.FineTuningJob.create(
    training_file=file_id,
    model=model_name
)

job_id = response['id']
print(f"Fine-tuning job created successfully with ID: {job_id}")
import openai

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read().strip()  # strip to remove any trailing whitespace or newline
    
def save_file(filepath, content):
    with open(filepath, 'a', encoding='utf-8') as outfile:
        outfile.write(content)

# (Replace 'YOUR_API_KEY_HERE' with your actual API key)
openai.api_key = "YOUR_API_KEY_HERE"

# Adjust the path to your data file
with open("YOUR PATH TO FINETUNE DATA", "rb") as file:
    response = openai.File.create(
        file=file,
        purpose='fine-tune'
    )

file_id = response['id']
print(f"File upload successfully with ID: {file_id}")

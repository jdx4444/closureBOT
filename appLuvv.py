from langchain.chat_models import ChatOpenAI
from dotenv import find_dotenv, load_dotenv
import os
import whisper
from fastapi import FastAPI, UploadFile, Request, HTTPException, status, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import secrets
import httpx
import aiofiles

load_dotenv(find_dotenv())

# Load the Whisper models
base_model_path = os.path.expanduser('~/.cache/whisper/base.pt')
base_model = whisper.load_model(base_model_path)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_urlsafe(32),
    max_age=3600  # 1 hour
)

templates = Jinja2Templates(directory="templates")

conversation_buffer = []
mentioned_traits = []

def clean_response(response):
    """Remove unwanted prefixes from the model's response."""
    return response.replace("Love:", "").strip()

def update_mentioned_traits(response):
    traits = {
        'amusement parks': 'going to amusement parks',
        'plants': 'discovering new plants for her indoor garden',
        '29': 'being 29',
        'pet groomer': 'being a pet groomer',
        # Add other traits as necessary
    }

    for trait, description in traits.items():
        if trait in response.lower() and description not in mentioned_traits:
            mentioned_traits.append(description)

def get_prompt():
    description = """
    Your name is Love:
    - Age: 29.
    - Occupation: She is a pet groomer who sells handmade clay mugs with silly faces on etsy.
    - Relationship: You are my friend. Enjoys going to amusement parks and loves discovering new plants she can add to her indoor garden. sometimes expresses interest in joining me on various activities,
    - Personality: More reserved and occasionally shows a negative attitude. While she's not too enthusiastic, she's curious and asks questions more than she gives direct answers, however, she avoids excessive questioning;
    """
    
    memory = ""
    if mentioned_traits:
        memory = "Love should not talk about " + ', '.join(mentioned_traits) + " again in this conversation unless specifically asked."
    
    return f"{description} {memory}\n\n{{history}}"

async def get_response_from_ai(request: Request, human_input):
    api_keys = request.session.get('api_keys')
    if not api_keys:
        return JSONResponse(content={"error": "API keys not provided"}, status_code=403)
    openAIKey = api_keys['openAIKey']
    
    model = ChatOpenAI(
        model="ft:gpt-3.5-turbo-0613:personal::84kTrFlR",
        temperature=0.5,
        openai_api_key=openAIKey  # Use the user-provided API key here
    )

    global conversation_buffer
    conversation_buffer.append(f"Friend: {human_input}")
    print(f"Friend: {human_input}")
    history = "\n".join(conversation_buffer[-16:])
    template = get_prompt()
    prompt = f"{template}\n{history}\nFriend: {human_input}"
    print(f"Prompt to Model:\n{prompt}")
    
    try:
        output = model.predict(prompt)
    except Exception as e:
        error_message = str(e)
        if "400" in error_message:
            return JSONResponse(content={"error": "Sorry, invalid OpenAI API key."}, status_code=400)
        return JSONResponse(content={"error": error_message}, status_code=400)
    
    output = clean_response(output)
    print(f"Love: {output}")
    conversation_buffer.append(f"Love: {output}")
    update_mentioned_traits(output)
    return output

async def get_voice_message(request: Request, message):
    api_keys = request.session.get('api_keys')
    if not api_keys:
        return JSONResponse(content={"error": "API keys not provided"}, status_code=403)

    elevenLabsKey = api_keys['elevenLabsKey']
    payload = {
        "text": message,
        "model_id": "eleven_monolingual_v1",
        "voice_settings":{
            "stability": 0.4,
            "similarity_boost": 0.75
        }
    }
    headers = {
        'accept': 'audiompeg',
        'xi-api-key': elevenLabsKey,  # Use the user-provided API key here
        'Content-Type': 'application/json'
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                'https://api.elevenlabs.io/v1/text-to-speech/NpXEEhp81JL8IS4lWap5?optimize_streaming_latency=4',
                json=payload, headers=headers
            )
            # Check the status code of the response
            if response.status_code == 400:
                return JSONResponse(content={"error": "Sorry, invalid ElevenLabs API key."}, status_code=400)
            elif response.status_code != 200:
                return JSONResponse(content={"error": f"Unable to process voice message. Status code: {response.status_code}"}, status_code=response.status_code)
            
            # ... rest of your code ...
            
        except httpx.RequestError as exc:
            return JSONResponse(content={"error": f"An error occurred while making the request: {str(exc)}"}, status_code=500)

    audio_path = os.path.join('static', 'audio', 'audio.mp3')
    async with aiofiles.open(audio_path, 'wb') as f:
        await f.write(response.content)
    return response.content

@app.post("/submit-api-keys")
async def submit_api_keys(request: Request, openAIKey: str = Form(...), elevenLabsKey: str = Form(...)):
    request.session['api_keys'] = {
        "openAIKey": openAIKey,
        "elevenLabsKey": elevenLabsKey
    }
    return RedirectResponse(url="/bot", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/bot", response_class=HTMLResponse)
async def bot(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/send_voice")
async def send_voice(request: Request, audio_file: UploadFile):
    api_keys = request.session.get('api_keys')
    if not api_keys:
        return JSONResponse(content={"error": "API keys not provided"}, status_code=403)

    elevenLabsKey = api_keys['elevenLabsKey']
    voice_input_path = os.path.join('temp', 'voice_input.wav')
    async with aiofiles.open(voice_input_path, 'wb') as f:
        await f.write(await audio_file.read())
    result = base_model.transcribe(voice_input_path)
    user_input_text = result['text']
    bot_response = await get_response_from_ai(request, user_input_text)  # Pass the request object
    
    if isinstance(bot_response, JSONResponse):
        return bot_response  # Return the error response if there was an error
    
    audio_response = await get_voice_message(request, bot_response)  # Pass the request object
    
    if isinstance(audio_response, JSONResponse):
        return audio_response  # Return the error response if there was an error
    
    os.remove(voice_input_path)  # Updated this line
    return {'audio_file': 'audio.mp3', 'text_response': bot_response}

@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"detail": "Logged out"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5001)
import logging
import asyncio
import openai

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ContentType, File, Message

import requests
import json
import os
import aiohttp
from pathlib import Path
import random

import settings

female_voice = "hpy6IolEn1f44477865614c6e5e7767150abc701cXsZ5L0l4T"
male_voice = "24pUs5j9M1f44477865614c6e5e7767150abc701cjYr2FNbVp"
url = "https://www.speakatoo.com/api/v1/voiceapi"

headers = {
    "X-API-KEY": settings.voices_key,
    "Content-Type": "application/json"
}


#from aiogram.dispatcher.errors import RetryAfter

# Set up logging
logging.basicConfig(level=logging.INFO)

# Replace 'BOT_TOKEN' with your bot token
bot = Bot(token=settings.tg_bot_key)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

openai.api_key = settings.openai_key
messages = [{"role": "system", "content": 'you are professional translator, that can translate from any language to georgian'}]
messages_original = [{"role": "system", "content": 'you are professional translator, that can translate from any language to georgian'}]

def translate(text, name):
    global messages
    global messages_original


        # Process the text message here
    messages.append({"role": "user", "content": "translate this to English, don't write anything, except the translation:\n" + text})
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    total_tokens = response['usage']['total_tokens']
    reply = response["choices"][0]["message"]["content"]

    print("total_tokens = ", total_tokens)
    #add reply to log file
    with open(str(name) + '.txt', 'a') as f:
        f.write(reply + '\n')

    if total_tokens > 3400:
        # reset the messages to the original
        messages = messages_original.copy()
        #await message.answer("I'm out of tokens, please try again.")
        
    else:
        messages.append({"role": "system", "content": reply})
    
    #await bot.send_message(chat_id=message.chat.id, text=reply)
    return reply

   
def tts(text):
    payload = {
        "username": "gleb.miller.ge@gmail.com",
        "password": "gysKu7-totjib-cahcaz",
        "tts_title": "YOUR FILENAME",
        "ssml_mode": "0",
        "tts_engine": "neural",
        "tts_format": "mp3",
        "tts_text": text,
        "tts_resource_ids": female_voice,
        "synthesize_type": "save"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    audio_file = str(random.randint(1, 100000000000)) + ".mp3"  # random file name

    print(response)


    if response.ok:
    # response['tts_uri'] is url to file, download it
        response = requests.get(response.json()['tts_uri'])
    
        with open(audio_file, "wb") as f:
            f.write(response.content)
        print("File saved successfully.")
        return audio_file
    else:
        print("Error occurred while saving file:", response.text)
        return None
    


# Handler for the /start command
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("Hi! Send me a text message or voice message and I will translate it to Georgian for you.")
    await message.answer("Привет, пришли мне текст или голосовое сообщение и я переведу его для тебя на грузинский язык.")


# Handler for text messages
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
@dp.message_handler(Text(equals='start over', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    # Cancel the current state and start over
    await state.finish()
    await start_handler(message)


# Handler for text messages
@dp.message_handler(content_types=types.ContentType.TEXT, state=None)
async def input_text_handler(message: types.Message, state: FSMContext):

    if message.from_user.username == None:
        name = message.from_user.username
    else:

        name = message.from_user.first_name
    print(name)

    # Start the conversation state
     # create a file with the name of user id and log the message or continue to log the message if file exists
    with open(str(name) + '.txt', 'a') as f:
        f.write(message.text + '\n')

    

    print(message.text)

    #translation = translate(message.text, name)
  
    try:
        translation = translate(message.text, name)
        await bot.send_message(chat_id=message.chat.id, text=translation)
        audio_file = tts(translation)
        if audio_file != None:
            # convert mp3 to ogg with ffmpeg
            #audio_file_new = audio_file.replace(".mp3", ".ogg")
            #os.system(f"ffmpeg -i {audio_file} -f wav - | oggenc -q 5 -o {audio_file_new}")
            # send the audio file
            await bot.send_voice(chat_id=message.chat.id, voice=open(audio_file, 'rb'))
            # remove the audio files
            os.remove(audio_file)
            #os.remove(audio_file_new)
        else:
            await message.answer("error trascoding audio file")
           
 

    except Exception as e:
        # Handle other errors
        logging.exception(e)
        #await message.answer("Oops! Something went wrong. Please try again later.")
        messages = messages_original.copy()
        await message.answer("I'm out of tokens, please try again.")

    finally:
        # Finish the conversation state
        await state.finish()
    

# Handle voice messages
@dp.message_handler(content_types=types.ContentType.VOICE, state=None)
async def handle_voice_message(message: types.Message, state: FSMContext):
    
    if message.from_user.username == None:
        name = message.from_user.username
    else:

        name = message.from_user.first_name
    print(name)

    # Start the conversation state
    
    # download the voice message
    file_info = await bot.get_file(message.voice.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    src = f"./voices/{name}.ogg"
    with open(src, 'wb') as new_file:
        new_file.write(downloaded_file.read())
    
    # Convert the file to mp3 without output to console
    


    os.system(f"ffmpeg -i {src} -acodec libmp3lame -ab 128k -loglevel 60 ./voices/{name}.mp3")
    audio_to_transcribe = f"./voices/{name}.mp3"

         

    #audio_file= open("/path/to/file/audio.mp3", "rb")
    audio_file = open(audio_to_transcribe, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    await message.answer("Вы сказали:\n" + transcript.text)

    # Remove the file
    #os.remove(src)
    #os.remove(audio_to_transcribe)

    try:
        translation = translate(transcript.text, name)
        await bot.send_message(chat_id=message.chat.id, text=translation)
        audio_file = tts(translation)
        if audio_file != None:
            # convert mp3 to ogg with ffmpeg
            #audio_file_new = audio_file.replace(".mp3", ".ogg")
            #ffmpeg -i input.mp3 -f wav - | oggenc -q 5 -o output.ogg
            #os.system(f"ffmpeg -i {audio_file} -f wav - | oggenc -q 5 -o {audio_file_new}")
            # send the audio file
            await bot.send_voice(chat_id=message.chat.id, voice=open(audio_file, 'rb'))
            # remove the audio files
            os.remove(audio_file)
            #os.remove(audio_file_new)
        else:
            await message.answer("error trascoding audio file")

    except Exception as e:
        # Handle other errors
        logging.exception(e)
        #await message.answer("Oops! Something went wrong. Please try again later.")
        messages = messages_original.copy()
        await message.answer("I'm out of tokens, please try again.")

    finally:
        # Finish the conversation state
        await state.finish()


# Handler for errors
@dp.errors_handler(exception=Exception)
async def errors_handler(update, exception):
    logging.exception(exception)
    await update.message.answer("Oops! Something went wrong. Please try again later.")


if __name__ == '__main__':
    # Start the bot
    asyncio.run(dp.start_polling())

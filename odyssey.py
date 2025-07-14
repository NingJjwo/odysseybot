import discord
import aiohttp
import json
import io
import os
import webserver
import threading
import time
import asyncio
from datetime import datetime
from discord import app_commands

DISCORD_TOKEN = os.environ['discordkey']
NASA_API_KEY = os.environ['nasakey']

intents = discord.Intents.all()

class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync(guild=discord.Object(id=889378727136493578))
            self.synced = True
        print(f"Bot connected as: {self.user}")

bot_client = Client()
tree = app_commands.CommandTree(bot_client)

@tree.command(
    guild=discord.Object(id=889378727136493578),
    name="apod",
    description="Picture of the Day"
)
async def apod(interaction: discord.Interaction):
    # Defer IMMEDIATELY before any processing
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        # Interaction already expired, can't respond
        print("Interaction expired before deferring")
        return
    except Exception as e:
        print(f"Error deferring interaction: {e}")
        return
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}"
            ) as response:
                if response.status != 200:
                    await interaction.followup.send(f"Error: Could not connect to NASA API (Status: {response.status}).")
                    return

                raw = await response.text()
                print(f"Raw API response: {raw}")
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await interaction.followup.send("Error: Could not parse API response.")
                    return

                if data.get("media_type") != "image":
                    await interaction.followup.send(
                        f"Today's content is not an image (media_type: {data.get('media_type')}). URL: {data.get('url')}"
                    )
                    return

                image_url = data.get("hdurl", data.get("url"))
                print(f"Image URL: {image_url}")

                async with session.head(image_url) as head_response:
                    content_type = head_response.headers.get("content-type", "")
                    print(f"Content-Type: {content_type}")
                    if not content_type.startswith("image/"):
                        await interaction.followup.send(
                            f"The link does not point to a valid image (Content-Type: {content_type}). URL: {image_url}"
                        )
                        return

                async with session.get(image_url) as img_response:
                    if img_response.status != 200:
                        await interaction.followup.send(f"Could not download image (Status: {img_response.status}). URL: {image_url}")
                        return
                    img_data = await img_response.read()
                    print(f"Downloaded image size: {len(img_data)} bytes")

                embed = discord.Embed(
                    title=data.get("title", "No Title"),
                    description=data.get("explanation", "No Description"),
                    timestamp=datetime.now(),
                    color=discord.Colour.blurple()
                )
                if "copyright" in data:
                    embed.add_field(name="Copyright", value=data["copyright"])

                file = discord.File(io.BytesIO(img_data), filename="apod.jpg")
                embed.set_image(url="attachment://apod.jpg")
                await interaction.followup.send(embed=embed, file=file)

                embed.set_footer(text=f"from {data.get('date', 'unknown')}")

    except discord.errors.NotFound:
        # Interaction expired, can't send followup
        print("Interaction expired, couldn't send response")
    except Exception as e:
        print(f"Error in apod command: {e}")
        try:
            await interaction.followup.send(f"An error occurred: {str(e)}")
        except discord.errors.NotFound:
            print("Couldn't send error message - interaction expired")

def start_discord_bot():
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            print(f"Attempting to start Discord bot (attempt {retry_count + 1}/{max_retries})")
            bot_client.run(DISCORD_TOKEN)
            break  # If successful, exit the loop
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited
                wait_time = 300 * (retry_count + 1)  # Exponential backoff: 5, 10, 15, 20, 25 minutes
                print(f"Rate limited. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                retry_count += 1
            else:
                print(f"Discord HTTP error: {e}")
                time.sleep(60)
                retry_count += 1
        except Exception as e:
            print(f"Discord bot error: {e}")
            time.sleep(60)
            retry_count += 1
    
    if retry_count >= max_retries:
        print("Max retries reached. Discord bot will remain offline.")
        print("Flask server will continue running.")

if __name__ == '__main__':
    # Start Flask server
    webserver.keep_alive()
    
    # Start Discord bot in a separate thread
    discord_thread = threading.Thread(target=start_discord_bot)
    discord_thread.daemon = True
    discord_thread.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
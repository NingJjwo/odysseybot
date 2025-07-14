import discord
import aiohttp
import json
import io
import os
import webserver
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
    await interaction.response.defer()
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}") as response:
                if response.status != 200:
                    await interaction.followup.send("Error connecting to NASA API.")
                    return
                
                data = await response.json()
                
                if data.get("media_type") != "image":
                    await interaction.followup.send(f"Today's content is not an image. URL: {data.get('url')}")
                    return
                
                image_url = data.get("hdurl", data.get("url"))
                
                async with session.get(image_url) as img_response:
                    if img_response.status != 200:
                        await interaction.followup.send("Could not download image.")
                        return
                    
                    img_data = await img_response.read()
                
                embed = discord.Embed(
                    title=data.get("title", "No Title"),
                    description=data.get("explanation", "No Description")[:2000],
                    timestamp=datetime.now(),
                    color=discord.Colour.blurple()
                )
                
                if "copyright" in data:
                    embed.add_field(name="Copyright", value=data["copyright"])
                
                embed.set_footer(text=f"from {data.get('date', 'unknown')}")
                
                file = discord.File(io.BytesIO(img_data), filename="apod.jpg")
                embed.set_image(url="attachment://apod.jpg")
                
                await interaction.followup.send(embed=embed, file=file)
                
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

async def main():
    # Start Flask server
    webserver.keep_alive()
    
    # Start Discord bot
    async with bot_client:
        await bot_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
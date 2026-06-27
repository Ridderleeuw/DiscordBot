def register(bot):
    @bot.event  # vroeg tygo: verandert de link naar een download video (maybe)
    async def on_message(message):
        if message.author == bot.user:
            return
        if "kill myself" in message.content.lower():
            await message.channel.send('https://cunnyx.com/realMax0r/status/1912444281601814819')
        await bot.process_commands(message)
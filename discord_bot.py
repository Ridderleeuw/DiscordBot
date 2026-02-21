import discord
from discord.ext import commands
import asyncio
import datetime
from logics import ssh_request_async, whitelist_logic, startserver, whitelist_update, shutdownserver, server_status, discover_Minecraft_servers, screen_check, load_discovered_servers
import os

#notities
#1 maak een plan van aanpak
#2 maak een flowchart van de bot   <ongoing>
#3 <done>whitelist fixen       zorg ervoor dat het op rgb update 
#4 <Done> startserver fixen   
#5 <Done> stakeholders request toevoegen
#6 <Done> auto discorvery van de servers maken (ook dat de commando's automatisch worden toegevoegd aan de bot)
#7 <done> moet een screen server hebben zodat we terug kunnen in de terminal.
#8 <done>minecraft server stoppen en daarna mogelijk maken om de server mee aftesluiten.
#9 /list function maken die naar screen <name> kijkt
#10 zorg ervoor dat als 1 screen al runt dat je die niet nog een keer kan starten op dezelfde server
#11 laat de server een /list doen voordat hij de server afsluit zodat de server niet aflsuit als de speler online is.
#12 palworld server toevoegen en update mogelijkheid maken
#couldhave# steam servers toevoegen zonder bemaning 

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='*', intents=intents, help_command=None)
intents.message_content = True


def run_bot(token):
    bot.run(token)


@bot.event
async def on_ready(): # run deze command als de bot online is
    load_discovery = await load_discovered_servers()
    print(f'Bot is online! Discovered servers: {list(load_discovery.keys())}')
    add_Minecraft_server(load_discovery)  #zorgt dat de auto discovery runt
    bot.loop.create_task(shutdown_22())

async def shutdown_22():
    while True:
        nu = datetime.datetime.now()
        if nu.hour == 22 and nu.minute == 0:
            if not server_status("192.168.178.201") and not server_status("192.168.178.202"):
                shutdownserver("m1")
                await bot.close()
                break
            else:
                print("Server is nog aan, dus niet afsluiten.")
        await asyncio.sleep(1800)



@bot.command(name="help")
async def custom_help(ctx, *, parameters=None):
    if parameters is None:
        embed = discord.Embed(title="Kelderman", color=discord.Color.green())
        embed.add_field(name="🔧 Kelderman commando's", value="Kelderman heeft wondervolle commando's.", inline=False)

        mc_servers = await load_discovered_servers()
        if mc_servers:
            embed.add_field(
                name="Beschikbare servers",
                value="\n".join(f"• `*`**{name}**" for name in mc_servers.keys()),
                inline=False
            )
        else:
            embed.add_field(name="Servers", value="Geen servers gevonden.", inline=False)

        embed.add_field(
            name="📃 Andere commando's",
            value="• `*help` – Laat het helpscherm zien, als je er niet uit komt, vraag ridderleeuw\n"
                  "• `*stopmc` – Stopt draaiende Minecraft servers\n"
                  "• `*whitelist` – Whitelist een speler\n"
                  "• `*palworld` – Start de Palworld server\n"
                  "• `*list` – Laat actieve spelers zien\n"
                  "• `*help advanced` – Laat geavanceerde commando's zien",
            inline=False
        )
        await ctx.send(embed=embed)

    elif parameters.lower() == "advanced":
        embed = discord.Embed(title="Kelderman - Geavanceerde Commando's", color=discord.Color.blue())
        embed.add_field(
            name="📜 Geavanceerde Commando's",
            value="• `*server` – start rgb/old server op\n"
                  "• `*shutdown` – sluit de server af\n"
                  "• `*runwhitelist` – whitelist wordt uitgevoerd op de servers\n"
                  "• `*autodiscovery` – kijkt of er nieuwe minecraft servers zijn\n",
            inline=False
        )
        await ctx.send(embed=embed)



#start server rgb and old
@bot.command()
async def server(ctx):
    await ctx.send("Wil je rgb of old starten? (rgb/old)")
    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel
    try:
        response = await bot.wait_for('message', check=check, timeout=30)
        if response.content.strip().lower() == "rgb":
            await ctx.send("RGB server wordt gestart.")
            await startserver(server="rgb")
        elif response.content.strip().lower() == "old":
            await ctx.send("Old server wordt gestart.")
            await startserver(server="old")
        else:
            await ctx.send("Ongeldige keuze. Kies rgb of old.")
        await ctx.send("server opgestart")
    except Exception as e:
        return None, f"verkeerd antwoord: {str(e)}"

#shutdown server
@bot.command()
async def shutdown(ctx, servernaam=None):
    if not servernaam:
        await ctx.send("Zet erachter welke server je wilt afsluiten (bijv: *shutdown rgb).")
        return

    await ctx.send(f"Wil je de server **{servernaam}** afsluiten? (ja/nee)")
    print(f"Aanvraag shutdown server: {servernaam}")

    def check(user_message):
        return user_message.author == ctx.author and user_message.channel == ctx.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=30)
        antwoord = response.content.strip().lower()

        if antwoord in ("ja","yes","y"):
            await ctx.send(f"{servernaam} server wordt afgesloten.")
            stdout, error = await shutdownserver(servernaam)
            print(f"shutdownserver returned → stdout: {stdout!r}, error: {error!r}")

            if not error:
                await ctx.send(f"{servernaam} server is succesvol afgesloten.")
                if servernaam == "m1":
                    await bot.close()
            else:
                await ctx.send(f"Fout bij afsluiten van {servernaam} server:\n{error}")

        elif antwoord in ("nee","no","n"):
            await ctx.send("Geannuleerd.")
            print("Shutdown geannuleerd door gebruiker.")

        else:
            await ctx.send("Antwoord niet herkend. Zeg 'ja' of 'nee'.")
            print("Antwoord niet herkend.")

    except asyncio.TimeoutError:
        await ctx.send("Je hebt te lang gewacht. Probeer het opnieuw.")
    except Exception as e:
        await ctx.send(f"Er ging iets mis: {e}")


#Whitelist
@bot.command()
async def whitelist(ctx):
    await ctx.send("Welk speler wil je whitelisten?")

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    try:
        # Wait for the player name
        response = await bot.wait_for('message', check=check, timeout=30)
        playername = response.content.strip()  # Extract the player name
        #regel dat playname, maar 1 word mag zijn zonder extenties of iets
        def is_valid_minecraft_name(name):
            if not (3 <= len(name) <= 16):
                return False
            for c in name:
                if not (c.isalnum() or c == "_"):
                    return False
            return True

        # Gebruik:
        if not is_valid_minecraft_name(playername):
            await ctx.send("Ongeldige spelernaam. Gebruik 3-16 letters, cijfers of underscores (geen spaties of tekens).")
            print("Naam is niet valid")
            return
        print(f"Whitelist aanvraag voor speler: {playername}")
        await ctx.send(f"Wil je {playername} whitelisten? (ja/nee)")

        confirmation = await bot.wait_for('message', check=check, timeout=30)
        if confirmation.content.strip().lower() in ["yes", "y", "ja"]:
            await ctx.send("Speler wordt toegevoegd aan de whitelist.")
            await whitelist_logic(playername)  # Pass the player name to the logic function
        elif confirmation.content.strip().lower() in ["no", "n", "nee", "verkeerde"]:
            await ctx.send("Vraag het dan niet.")
            await ctx.send("JK, zou je het nog een keer willen proberen? 😘")

    except asyncio.TimeoutError:
        await ctx.send("Je hebt te lang gewacht. Probeer het opnieuw.")
    except Exception as e:
        await ctx.send(f"Begreep je niet: {str(e)}")

@bot.command()
async def runwhitelist(ctx):
    whitelist_update() #update the whitelist als het nodig is
    await ctx.send("Whitelist is geupdate.")


def add_Minecraft_server(servers):
    global last_started_server

    for name, path in servers.items():
        if name in bot.commands:
            continue  # Skip als command al bestaat

        def make_command(server_name, server_path):
            async def server_command(ctx, _server_name=server_name, _server_path=server_path):
                global last_started_server
                last_started_server = _server_name
                directory = os.path.dirname(_server_path)
                await ctx.send(f"Starting Minecraft server: **{_server_name}**")

                # Start de RGB-server in een threadpool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, startserver, "rgb")

                # Start whitelist update in achtergrond
                #asyncio.create_task(whitelist_update())
                async def screen_status():
                        screen_check_Variable = await screen_check()
                        if not screen_check_Variable:
                            output, error = await ssh_request_async("rgb", f"screen -dmS {_server_name}_server bash -c 'cd {directory} && bash {os.path.basename(_server_path)}'")
                            if error:
                                await ctx.send(f"Fout bij starten van **{_server_name}**:\n```{error}```")
                            else:
                                await ctx.send(f"**{_server_name}** is gestart in een screen sessie.")
                        else:
                            await ctx.send(f"Screen sessie draait al. {output} is actief.")

                servercheck =  await server_status("rgb")
                if servercheck:
                    await screen_status()
                else:
                    result = await startserver(server="rgb")
                    if result:
                        print("server succesvol gestart | nu service starten")
                        await screen_status()
                    else:
                        await ctx.send(f"Fout bij starten van rgb-server is.")
                        
            return server_command

        command_func = make_command(name, path)
        bot.command(name=name)(command_func)


#close minecraft server
@bot.command()
async def stopmc(ctx, server_name: str = None):
    global last_started_server  # Gebruik de globale variabele
    if not server_name:
        if not last_started_server:
            await ctx.send("Er is geen server bekend die het laatst is opgestart. Staat er een Minecraft-server aan? Zo nee, gebruik het shutdown-commando.")
            succes, session = await screen_check()
            if succes:
                server_name = session[0]
            return
        
        server_name = last_started_server  # Gebruik de laatst opgestarte server
    
    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel
    try:
        await ctx.send(f"Wil je de {server_name} afsluiten? (ja/nee)")
        response = await bot.wait_for('message', check=check, timeout=30)
        antwoord = response.content.strip().lower()
        if antwoord in ["ja", "yes", "y"]:
            await ctx.send(f"De minecraftserver {server_name}  wordt afgesloten.")
            await ssh_request_async("rgb", f"screen -S {server_name}_server -X stuff 'stop\n'") 
            print(f"Server {server_name} is afgesloten.")
            await ctx.send ("Wil je de fysieke server afsluiten? (ja/nee)")
            response = await bot.wait_for('message', check=check, timeout=30)
            antwoord = response.content.strip().lower()
            if antwoord in ["ja", "yes", "y"]:
                await ctx.send("De fysieke server wordt afgesloten.")
                await shutdownserver("rgb")
            elif antwoord in ["nee", "no"]:
                await ctx.send("De fysieke server blijft aan.")
        elif antwoord in ["nee", "no"]:
            await ctx.send(f"De minecraftserver {server_name} blijft aan.")
    except asyncio.TimeoutError: 
        await ctx.send("Je hebt te lang gewacht. De server blijft aan.")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")


#/list
@bot.command()  ## werkt veelkans niet omdat de screen output niet gestreamline kan worden naar de script.
async def list(ctx, server_name: str = None):
    global last_started_server
    if not server_name:
        if not last_started_server:
            await ctx.send("Er is geen server bekend die het laatst is opgestart. Staat er een Minecraft-server aan? Zo nee, gebruik het shutdown-commando.")
            return
        server_name = last_started_server  # Gebruik de laatst opgestarte server
    output, error = await ssh_request_async("rgb", f"screen -S {server_name}_server -X stuff 'list\n'")
    if error:
        await ctx.send(f"error met list vragen {server_name}: {error}")
    else:
        await ctx.send(f" Players zijn online: {output}")
    
#steam 
@bot.command()
async def palworld(ctx):
    await ctx.send("Wil je de palworld server starten? (ja/nee)")

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    try:
        # Wait for the player name
        response = await bot.wait_for('message', check=check, timeout=30)
        if response.content.strip().lower() in ["yes", "y", "ja"]:
            await ctx.send("Palworld server wordt gestart.")
            asyncio.create_task(startserver(server="old"))
        elif response.content.strip().lower() in ["no", "n", "nee"]:
            await ctx.send("Vraag het dan niet.")
            await ctx.send("JK, zou je het nog een keer willen proberen? 😘")
    except asyncio.TimeoutError:
        await ctx.send("Je hebt te lang gewacht. Probeer het opnieuw.")
    except Exception as e:
        await ctx.send(f"Begreep je niet: {str(e)}")

@bot.command()
async def autodiscovery(ctx):
    await ctx.send ("Auto-discovery van Minecraft-servers wordt uitgevoerd...")
    result = await discover_Minecraft_servers("minecraft_autodiscovery")
    if isinstance(result, str):
        await ctx.send(f"Fout bij auto-discovery:\n {result}")
    elif isinstance(result, dict) and result:
        await ctx.send("Auto-discovery succesvol:\n" + "\n".join(f"• {k}" for k in result.keys()))
    else:
        await ctx.send("Geen servers gevonden.")

## zinloze stuf

@bot.event #vroeg tygo    veranderd de link naar een download video (maybe)
async def on_message(message):
    if message.author == bot.user:
        return
    if "kill myself" in message.content.lower():
        await message.channel.send('https://cunnyx.com/realMax0r/status/1912444281601814819')
    await bot.process_commands(message)



import disnake
from disnake.ext import tasks, commands
import shelve
import locale
import dotenv, os
import sys, logging
import random
from datetime import date, time, timedelta, datetime
import time as t

# Set locale
locale.setlocale(locale.LC_ALL,'fr_FR')

# Get info from the env file
dotenv.load_dotenv()
token = os.getenv('TOKEN')
guild_id = int(os.getenv('GUILD_ID'))
sessions_channel_id = int(os.getenv('SESSIONS_CHANNEL_ID'))
invite_link = os.getenv('INVITE_LINK')

# Set intents
intents = disnake.Intents.all()

# Setup logging
logger = logging.getLogger('disnake')
logger.setLevel(logging.DEBUG)
txthandler = logging.FileHandler(filename=f"logs\\{datetime.now().date()}_{datetime.now().time().strftime('%H%M%S')}_BarBaz.log", encoding='utf-8', mode='w')
txthandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(txthandler)
consolehandler = logging.StreamHandler(stream=sys.stdout)
consolehandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(consolehandler)

# Class definitions
class GameSession:
    '''A session object used by the bot'''
    def __init__(self, author_id, message_id, role_id, start, duration, desc):
        self.author_id = author_id
        self.message_id = message_id
        self.role_id = role_id
        self.start = start
        self.duration = duration
        self.end = self.start + duration
        self.has_ended = False
        self.expiration = self.start + timedelta(days=7)
        self.desc = desc
        self.present = []
        self.notpresent = []
        self.maybepresent = []
        
    async def update_message(self):
        guild = bot.get_guild(guild_id)
        sessions_channel = bot.get_channel(sessions_channel_id)
        message = await sessions_channel.fetch_message(self.message_id)
        author = guild.get_member(self.author_id)
        role = guild.get_role(self.role_id)
        date_string = self.start.date().strftime('%A %d %B %Y')
        time_string = self.start.time().strftime('%Hh%M')
        new_content = f"**{author.mention} propose une session {role.mention} le {date_string} ?? {time_string} :**\n> *{self.desc}*\n_ _"
        
        if len(self.present) > 0:
            new_content += "\nParticipent :"
            for member_id in self.present:
                new_content += f"\n{guild.get_member(member_id).mention}"
        if len(self.notpresent) > 0:
            new_content += "\nNe participent pas :"
            for member_id in self.notpresent:
                new_content += f"\n{guild.get_member(member_id).mention}"
        if len(self.maybepresent) > 0:
            new_content += "\nParticipent peut-??tre :"
            for member_id in self.maybepresent:
                new_content += f"\n{guild.get_member(member_id).mention}"
        # If role is random, select random game
        if (role.name == 'random' or role.name == 'misc') and len(self.present) > 0:
            all_games = []
            for member_id in self.present:
                member = guild.get_member(member_id)
                for member_role in member.roles:
                    exists = False
                    for game_choice in all_games:
                        if game_choice.role == member_role:
                            game_choice.counter += 1
                            exists = True
                    if exists == False and member_role in game_roles:
                        new_game = GameChoice(member_role, member_role.name)
                        new_game.counter = 1
                        all_games.append(new_game)
            common_games = []
            for game_choice in all_games:
                if game_choice.counter == len(self.present):
                    common_games.append(game_choice)
            random_game = random.choice(common_games)
            # Update message with random game
            new_content += f"\n\n{bot.user.mention} propose un jeu au hasard : {random_game.name}"
        
        # Send the updated message
        await message.edit(content=new_content)

class GameChoice:
    '''A game choice object used for random game choice'''
    def __init__(self, role, name):
        self.role = role
        self.name = name
        self.counter = 0

# Let's go
bot = commands.InteractionBot(intents=intents, sync_commands_debug=True)

# Global variables
game_roles = []
barbaz_topics = commands.option_enum(os.listdir('help_files\\barbaz'))
titanfall_topics = commands.option_enum(os.listdir('help_files\\titanfall'))
sart_topics = commands.option_enum(os.listdir('help_files\\sart'))

@bot.event
async def on_ready():
    guild = bot.get_guild(guild_id)
    sessions_channel = bot.get_channel(sessions_channel_id)
    guild_roles = await guild.fetch_roles()
    for role in guild_roles:
        if role.name in ['misc', 'Deep Rock Galactic', 'Golf It!', 'GTA Online', 'Guild Wars 2', 'Hunt: Showdown', 'Left 4 Dead 2', 'Overwatch 2', 'Rocket League', 'Sonic & All-Stars Racing Transformed', 'Star Wars Battlefront II', 'Titanfall 2']:
            game_roles.append(role)
    print('The bot is ready!')

# Loops go here
# This one looks for ended and expired sessions to purge them
@tasks.loop(hours=1)
async def update_sessions():
    sessions_channel = bot.get_channel(sessions_channel_id)
    with shelve.open('data\\game_sessions') as game_sessions:
        for game_session in game_sessions:
            session = game_sessions[game_session]
            if datetime.now() > session.end and session.has_ended == False:
                message = await sessions_channel.fetch_message(session.message_id)
                message_content = message.content
                message_content += "\n\n**Cette session est termin??e** !"
                await message.edit(content=message_content, components=None)
                session.has_ended = True
                game_sessions[game_session] = session
            if datetime.now() > session.expiration:
                message = await sessions_channel.fetch_message(session.message_id)
                await message.delete()
                del game_sessions[game_session]

update_sessions.start()

# Wait until the bot is ready before we start the loop
@update_sessions.before_loop
async def before_update_sessions():
    await bot.wait_until_ready()

# Slash commands go here
@bot.slash_command(name='new-session', description='Cr???? une session de jeu et la poste dans le canal appropri??')
async def new_session(inter: disnake.ApplicationCommandInteraction,
                      role: disnake.Role = commands.Param(name='role', description='R??le pour le jeu de la session'),
                      session_date: str = commands.Param(default=None, name='date', description='Date de la session. Exemple : 2023-01-28'),
                      session_time: str = commands.Param(default=None, name='time', description='Heure de la session. Exemple : 21:30'),
                      session_duration: int = commands.Param(ge=1, le=6, default=None, name='last', description='Dur??e de la session en heures. Exemple : 3'),
                      session_desc: str = commands.Param(default=None, name='desc', description='Description de la session. Exemple : Missions de pr??paration, pause vers 22:30')):

    # Defer the real answer to buy time
    await inter.response.defer(ephemeral=True)

    # Apply default values
    if session_date == None:
        session_date = datetime.now().date().isoformat()
    if session_time == None:
        session_time = datetime.now().time().isoformat()
    if session_duration == None:
        session_duration = 3
    if session_desc == None:
        session_desc = 'Des gens int??ress??s ?'

    # Convert strings into proper types
    try:
        session_date = date.fromisoformat(session_date)
    except:
        await inter.edit_original_response(content='Une erreur est survenue. Veuillez rentrer une date valide au format ISO. Exemple : 2023-01-28')
    try:
        session_time = time.fromisoformat(session_time)
    except:
        await inter.edit_original_response(content='Une erreur est survenue. Veuillez rentrer une heure valide au format ISO. Exemple : 21:30')
    try:
        session_duration = timedelta(hours=session_duration)
    except:
        await inter.edit_original_response(content='Une erreur est survenue. Veuillez rentrer une dur??e valide. Exemple : 3')
    session_start = datetime.combine(session_date, session_time)

    # Format them
    session_date = session_date.strftime("%A %d %B %Y")
    session_time = session_time.strftime("%Hh%M")

    # Get the Sessions channel
    sessions_channel = bot.get_channel(sessions_channel_id)

    # Send a session message
    session_message = await sessions_channel.send(
        f"**{inter.author.mention} propose une session {role.mention} le {session_date} ?? {session_time} :**\n> *{session_desc}*\n_ _",
    )

    with shelve.open('data\\game_sessions') as game_sessions:
        # Create session object
        new_session = GameSession(inter.author.id, session_message.id, role.id, session_start, session_duration, session_desc)
        # Add it to the shelf
        game_sessions[str(session_message.id)] = new_session

    # Add buttons to it and create their ids based on the message id
    await session_message.edit(
        components=[disnake.ui.Button(label='Je participe', style=disnake.ButtonStyle.success, custom_id=f"{session_message.id + 1}"),
                    disnake.ui.Button(label='Je ne participe pas', style=disnake.ButtonStyle.danger, custom_id=f"{session_message.id + 2}"),
                    disnake.ui.Button(label='Je participe peut-??tre', style=disnake.ButtonStyle.secondary, custom_id=f"{session_message.id + 3}"),
                    ],
    )

    # Respond to the initial command interaction
    await inter.edit_original_response(content='Session cr????e !')

@bot.slash_command(name='get-session', description='Donne la liste des sessions existantes')
async def get_sessions(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer(ephemeral=True)

    with shelve.open('data\\game_sessions') as game_sessions:
        if len(game_sessions) > 0:
            list_session = "__**Voici les sessions actives :**__\n"
            for i, game_session in enumerate(game_sessions):
                session = game_sessions[game_session]
                if datetime.now() < session.end and session.has_ended == False:
                    list_session += f'**Session n??{(i + 1)} :**\n      **ID du message :** `{session.message_id}`\n      **Jeu :** {bot.get_guild(guild_id).get_role(session.role_id).mention}\n      **Description :** {session.desc}\n      **Commence :** <t:{int(t.mktime(session.start.timetuple()))}:R>\n      **Finit :** <t:{int(t.mktime(session.end.timetuple()))}:R>'
            list_session += "\n\n *L'ID du message peut ??tre utilis?? avec la commande /edit-session [ID du message]*"
            await inter.edit_original_response(content=list_session)
        else:
            await inter.edit_original_response(content='**Il n\'y a aucune session active pour le moment.**')


@bot.slash_command(name='edit-session', description='Modifie une session de jeu existante')
async def edit_session(inter: disnake.ApplicationCommandInteraction,
                      message_id: str = commands.Param(name='id', description='Id du message de la session. R??cup??rable avec /get-session'),
                      role: disnake.Role = commands.Param(default=None, name='role', description='R??le pour le jeu de la session'),
                      session_date: str = commands.Param(default=None, name='date', description='Date de la session. Exemple : 2023-01-28'),
                      session_time: str = commands.Param(default=None, name='time', description='Heure de la session. Exemple : 21:30'),
                      session_duration: int = commands.Param(ge=1, le=6, default=None, name='last', description='Dur??e de la session en heures. Exemple : 3'),
                      session_desc: str = commands.Param(default=None, name='desc', description='Description de la session. Exemple : Missions de pr??paration, pause vers 22:30')):

    # Defer the real answer to buy time
    await inter.response.defer(ephemeral=True)

    with shelve.open('data\\game_sessions') as game_sessions:
        session = game_sessions[message_id]
        sessions_channel = bot.get_channel(sessions_channel_id)
        message = await sessions_channel.fetch_message(message_id)

        # Apply new values if need be
        if role != None:
            session.role = role
        if session_date != None:
            try:
                session_date = date.fromisoformat(session_date)
            except:
                await inter.edit_original_response(content='Une erreur est survenue. Veuillez rentrer une date valide au format ISO. Exemple : 2023-01-28')
            session.start = datetime.combine(session_date, session.start.time())
            session.end = session.start + session.duration
            session.expiration = session.start + timedelta(days=1)
        if session_time != None:
            try:
                session_time = time.fromisoformat(session_time)
            except:
                await inter.edit_original_response(content='Une erreur est survenue. Veuillez rentrer une heure valide au format ISO. Exemple : 21:30')
            session.start = datetime.combine(session.start.date(), session_time)
            session.end = session.start + session.duration
            session.expiration = session.start + timedelta(days=1)
        if session_duration != None:
            try:
                session_duration = timedelta(hours=session_duration)
            except:
                await inter.edit_original_response(content='Une erreur est survenue. Veuillez rentrer une dur??e valide. Exemple : 3')
            session.duration = session_duration
            session.end = session.start + session.duration
        if session_desc != None:
            session.desc = session_desc
        
        game_sessions[message_id] = session

        await session.update_message()
    # Respond to the initial command interaction
    await inter.edit_original_response(content='Session modifi??e !')

@bot.slash_command(name='remove-session', description='Supprime une session de jeu existante')
async def remove_session(inter: disnake.ApplicationCommandInteraction,
                         message_id: str = commands.Param(name='id', description='Id du message de la session. R??cup??rable avec /get-session')):

    # Defer the real answer to buy time
    await inter.response.defer(ephemeral=True)

    with shelve.open('data\\game_sessions') as game_sessions:
        session = game_sessions[message_id]
        sessions_channel = bot.get_channel(sessions_channel_id)
        message = await sessions_channel.fetch_message(message_id)

        if inter.author.id == session.author_id:
            await message.delete()
            del game_sessions[message_id]
            await inter.edit_original_response(content='Session supprim??e !')
        else:
            await inter.edit_original_response(content='Impossible : vous n\'??tes pas l\'auteur de la session !')

@bot.slash_command(name='remove-message', description='Supprime des messages', default_member_permissions=disnake.Permissions(manage_messages=True))
async def remove_message(inter: disnake.ApplicationCommandInteraction,
                         amount: int = commands.Param(ge=1, le=100, name='amount', description='Nombre de messages ?? supprimer en partant du plus r??cent. Exemple : 5')):

    # Defer the real answer to buy time
    await inter.response.defer()
    # Delete messages
    current_channel = bot.get_channel(inter.channel_id)
    await current_channel.purge(limit=amount + 1)

@bot.slash_command(name='get-invitelink', description='Donne le lien pour inviter des gens sur le serveur')
async def get_invitelink(inter: disnake.ApplicationCommandInteraction):
    # Defer the real answer to buy time
    await inter.response.defer(ephemeral=True)
    await inter.edit_original_response(content=invite_link)

@bot.slash_command(name='set-role', description='Permet d\'??diter les r??les que vous avez. Retirer / Ajouter un jeu ?? votre utilisateur')
async def set_role(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer(ephemeral=True)
    message_content = "Voici l'??tat actuel de vos r??les :\n"
    message_components = []
    for role in game_roles:
        message_components.append(disnake.ui.Button(label=f'{role.name}', style=disnake.ButtonStyle.primary, custom_id=f"{inter.id}_{role.name}"))
        if role in inter.author.roles:
            message_content += f"??? {role.mention}\n"
        else:
            message_content += f"??? {role.mention}\n"
    await inter.edit_original_response(content=message_content, components=message_components)

@bot.slash_command(name='get-help', description='Affiche de l\'aide')
async def get_help(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer(ephemeral=True)
    pass

@get_help.sub_command(name='commands', description='Affiche de l\'aide sur les commandes de BarBaz')
async def commands_help(inter: disnake.ApplicationCommandInteraction,
                        topic: str = commands.Param(name='topic', description='Le fichier d\'aide ?? ouvrir', choices=barbaz_topics)):
    with open(f'help_files\\barbaz\\{topic}', 'r', encoding='utf-8') as help_file:
        help_content = help_file.read()
        await inter.edit_original_response(content=help_content)

@get_help.sub_command(name='titanfall', description='Affiche de l\'aide sur Titanfall 2')
async def titanfall_help(inter: disnake.ApplicationCommandInteraction,
                         topic: str = commands.Param(name='topic', description='Le fichier d\'aide ?? ouvrir', choices=titanfall_topics)):
    with open(f'help_files\\titanfall\\{topic}', 'r', encoding='utf-8') as help_file:
        help_content = help_file.read()
        await inter.edit_original_response(content=help_content)

@get_help.sub_command(name='sart', description='Affiche de l\'aide sur Sonic & All-Stars Racing Transformed')
async def sart_help(inter: disnake.ApplicationCommandInteraction,
                         topic: str = commands.Param(name='topic', description='Le fichier d\'aide ?? ouvrir', choices=sart_topics)):
    with open(f'help_files\\sart\\{topic}', 'r', encoding='utf-8') as help_file:
        help_content = help_file.read()
        await inter.edit_original_response(content=help_content) 

# Listeners
@bot.listen('on_button_click')
async def rsvp_listener(inter: disnake.MessageInteraction):
    # Filter irrelevant button presses
    if inter.component.label not in ['Je participe', 'Je ne participe pas', 'Je participe peut-??tre']:
        return
    
    # Reverse the id generation for the buttons to get the original message id
    message_id = 0
    match inter.component.label:
        case 'Je participe':
            message_id = int(inter.component.custom_id) - 1
        case 'Je ne participe pas':
            message_id = int(inter.component.custom_id) - 2
        case 'Je participe peut-??tre':
            message_id = int(inter.component.custom_id) - 3

    # Work in the relevant session object
    with shelve.open('data\\game_sessions') as game_sessions:
        session = game_sessions[str(message_id)]
        present = session.present
        notpresent = session.notpresent
        maybepresent = session.maybepresent

        if inter.author.id in present:
            present.remove(inter.author.id)
        elif inter.author.id in notpresent:
            notpresent.remove(inter.author.id)
        elif inter.author.id in maybepresent:
            maybepresent.remove(inter.author.id)

        # Register the member in the correct list
        if inter.component.label == 'Je participe':
            await inter.response.defer()
            present.append(inter.author.id)
        elif inter.component.label == 'Je ne participe pas':
            await inter.response.defer()
            notpresent.append(inter.author.id)
        elif inter.component.label == 'Je participe peut-??tre':
            await inter.response.defer()
            maybepresent.append(inter.author.id)
        
        game_sessions[str(message_id)] = session

        await session.update_message()

@bot.listen('on_button_click')
async def setrole_listener(inter: disnake.MessageInteraction):
    # Filter irrelevant button presses
    if inter.component.label not in ['misc', 'Deep Rock Galactic', 'Golf It!', 'GTA Online', 'Guild Wars 2', 'Hunt: Showdown', 'Left 4 Dead 2', 'Overwatch 2', 'Rocket League', 'Sonic & All-Stars Racing Transformed', 'Star Wars Battlefront II', 'Titanfall 2']:
        return

    for role in game_roles:
        if role.name == inter.component.label:
            if role in inter.author.roles:
                await inter.author.remove_roles(role)
            else:
                await inter.author.add_roles(role)
            await set_role(inter)

bot.run(token)
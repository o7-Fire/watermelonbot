from datetime import datetime
import discord
import json
import pymongo
import asyncio
import random
from discord.ext import commands
from mastermelon import counting_bot, show_countries, console_commands
from mastermelon import highlow_game
from mastermelon import giveaway_bot
from mastermelon import effects_display
from mastermelon import emojis as ej
from mastermelon import cookiegame
from mastermelon import gen_image


def get_latest_exp(res, convertedexp_doc):
    muuid = {}
    muuid_name = {}
    last_updated = {}
    exp_dict = {}
    if convertedexp_doc is None:
        convertedexp_doc = {}
    for doc in res:
        if doc["EXP"] is None:
            doc["EXP"] = 0
        if doc["muuid"] not in muuid:
            muuid[doc["muuid"]] = {doc["servername"]: doc["EXP"]}
            muuid_name[doc["muuid"]] = doc["musername"]
            last_updated[doc["muuid"]] = {doc["servername"]: doc["date"]}
        elif (doc["servername"] in muuid[doc["muuid"]]) and (muuid[doc["muuid"]][doc["servername"]] < doc["EXP"]):
            muuid[doc["muuid"]][doc["servername"]] = doc["EXP"]
            muuid_name[doc["muuid"]] = doc["musername"]
            last_updated[doc["muuid"]][doc["servername"]] = doc["date"]
        else:
            muuid[doc["muuid"]][doc["servername"]] = doc["EXP"]
            last_updated[doc["muuid"]][doc["servername"]] = doc["date"]
        if doc["muuid"] not in convertedexp_doc:
            convertedexp_doc[doc["muuid"]] = {}
    str_builder = ""
    for muuid_i, exps in muuid.items():
        str_builder += "In Game Name: `" + muuid_name[muuid_i] + "`\n"  # +str(exps) +"\n"
        exp_builder = ""
        muuid_exp_dict = {"In_Game_Name": muuid_name[muuid_i], "servers": []}
        for server, exp in sorted(list(exps.items()),
                                  key=lambda x: 0 if isinstance(x[1], type(None)) else x[1], reverse=True):
            if server in ["ALEX | ATTACK SERVER", "ALEX | PVP SERVER", "ALEX | SURVIVAL SERVER",
                          'ALEX | TURBO PVP SERVER', "ALEX | PVP SERVER (ASIA)", "ALEX | HEX SERVER"]:
                try:
                    exp = 0 if exp is None else exp
                    rservername = server[7:].replace(" SERVER", "")
                    serverstr = rservername + (
                        " [TOP 1%]" if exp > 40000 else (" [TOP 10%]" if exp > 15000 else ""))
                    if server[7:].replace(" SERVER", "") not in convertedexp_doc[muuid_i]:
                        convertedexp_doc[muuid_i][rservername] = {"claimed": 0, "lcdate": None}
                        claimed = 0
                        lcdate = None
                    else:
                        claimed = convertedexp_doc[muuid_i][rservername]["claimed"]
                        lcdate = convertedexp_doc[muuid_i][rservername]["lcdate"]
                    exp_builder += f"{exp:>6}  " + f"{serverstr:<21}" + \
                                   last_updated[muuid_i][server].strftime("%Y-%m-%d %H:%M") + f"   {claimed:<6}" + "\n"
                    muuid_exp_dict["servers"].append({"servername": rservername,
                                                      "exp": exp, "claimed": claimed, "lcdate": lcdate,
                                                      "lupdated": last_updated[muuid_i][server]
                                                      })
                except Exception as e:
                    print(exp, server)
                    print(str(e))
        if len(exp_builder) > 0:
            exp_builder = "```\n <EXP>  <SERVER>             <LASTUPDATED,UTC>  <CLAIMED>\n" + exp_builder + "\n```"
            str_builder += exp_builder
            exp_dict[muuid_i] = muuid_exp_dict
    return str_builder, exp_dict, convertedexp_doc


intents = discord.Intents.default()
intents.members = True

description = '''An example bot to showcase the discord.ext.commands extension
module.

There are a number of utility commands being showcased here.'''

with open("watermelon.config", "rb") as f:
    js = json.load(f)
    mongo_key: str = js["mongo_key"]
    prefix: str = js["prefix"]

if prefix in ["w?", "t?"]:  # only access mongodb for w? and t?
    client = pymongo.MongoClient(mongo_key)
    db = client.get_database("AlexMindustry")
    expgains = db["expgains"]
    convertedexp = db["convertedexp"]
    ax = db["ax"]
    ingamecosmetics = db["ingamecosmetics"]
    ipaddress_access_key: str = js["ipaddress_access_key"]
    serverplayerupdates = db["serverplayerupdates"]
    discordinvites: pymongo.collection = db["discordinvites"]

invitecode_mapping = {"KPVVsj2MGW": "Doge Mindustry Invite", "BnBf2STAAd": "Doge Youtube Invite",
                      "GSdkpZZuxN": "Doge Youtube Premium Invite", "BmCssqnhX6": "Alex TOP MC Invite",
                      "FpKnzzQFne": "Alex TOP MC SERVERS Invite", "EhzVgNGxPD":"Doge Annoucement Invite",
                      "A33dUt6r7n": "Alex Factorio Invite"}


class bb(commands.Bot):

    def __init__(self, command_prefix, *args, **options):
        self.invites = {}
        self.inviter_dict = {}
        super().__init__(command_prefix, *args, **options)

    async def on_member_join(self, member: discord.Member):
        if prefix == "t?":
            return
        guild: discord.Guild = member.guild
        if member.bot:
            return
        invites_before_join = self.invites[member.guild.id]
        invites_after_join = await member.guild.invites()
        total_members = len([m for m in guild.members if not m.bot])

        curr_invite: discord.guild.Invite
        existing_invite: discord.guild.Invite
        found_resp_invite = False
        resp_invite: discord.guild.Invite
        for curr_invite in invites_after_join:
            found_old_invite = False
            for existing_invite in invites_before_join:
                if curr_invite.code == existing_invite.code:
                    found_old_invite = True
                    if curr_invite.uses > existing_invite.uses:
                        found_resp_invite = True
                        resp_invite = curr_invite  # this is the invite that was used
            if not found_old_invite:
                await self.update_self_invite_dict(guild, curr_invite)
                # update mongo with the new entry
                discordinvites.find_one_and_update({"duuid": curr_invite.inviter.id},
                                                   {"$set": {"codes." + curr_invite.code: curr_invite.uses}})
                if curr_invite.uses > 0:
                    found_resp_invite = True
                    resp_invite = curr_invite

        if found_resp_invite:
            # type the msg here
            invite = resp_invite
            # add the invited member to the inviter's list
            invite_dict_info = {"invited": {"name": f"{member.name}#{member.discriminator}", "duuid": member.id,
                                            "date": datetime.utcnow()}}
            discordinvites.find_one_and_update({"duuid": invite.inviter.id}, {"$push": invite_dict_info})
            print(f"Member {member.name} Joined. Invite Code: {invite.code}. Inviter: {invite.inviter}")
            if invite.code in invitecode_mapping:
                to_send = f'{member.mention}, you are the #{total_members} member' + \
                          f".\n Inviter: {invitecode_mapping[invite.code]}. \nInvite counts: {invite.uses}"
            else:
                to_send = f'{member.mention}, you are the #{total_members} member' + \
                          f".\nInvite Code: {invite.code}. Inviter: {invite.inviter}. \nInvite counts: {invite.uses}"
        else:
            # invite code unknown.
            to_send = f'{member.mention}, you are the #{total_members} member' + \
                      f".\n Unable to identify invite code."

        # todo everytime someone joins, compare old invite list to new invite list
        # find the invitecode with the increment OR with a new invitecode with >1 invite
        #   # print it out
        # save all invites to invite list
        self.invites[member.guild.id] = invites_after_join

        if guild.system_channel is not None:
            embed = discord.Embed(colour=discord.Colour.random().value)
            embed.add_field(name=f"Welcome to {guild.name}!", value=to_send)
            embed.set_thumbnail(url=str(member.avatar_url))

            avatar = member.avatar_url_as(format="png", static_format="png", size=64)
            name = f"{member.name}#{member.discriminator}"
            image_data = await gen_image.getwelcomeimage(name=name, avatar=avatar)
            await guild.system_channel.send(embed=embed,file=image_data)

    async def on_member_remove(self, member: discord.Member):
        # Updates the cache when a user leaves to make sure everything is up to date
        invites_before_remove = self.invites[member.guild.id]
        invites_after_remove = await member.guild.invites()
        self.invites[member.guild.id] = await member.guild.invites()
        guild: discord.Guild = member.guild
        msg_builder = f'`{member.display_name.replace("`", "")}` left ;-;'
        total_members = len([m for m in guild.members if not m.bot])
        for invite in invites_before_remove:
            if invite.uses > find_invite_by_code(invites_after_remove, invite.code).uses:
                msg_builder += f" {member.display_name}, -1 invite for Invite Code: {invite.code}. Inviter: {invite.inviter}"
        await guild.system_channel.send(msg_builder + f"\nNow we have {total_members} members.")

    async def on_ready(self):
        print('Logged in as', bot.user.name, bot.user.id)
        for guild in bot.guilds:
            # Adding each guild's invites to our dict
            self.invites[guild.id] = await guild.invites()
            self.inviter_dict[guild.id] = {}
            invite: discord.guild.Invite
            for invite in self.invites[guild.id]:
                await self.update_self_invite_dict(guild, invite)

    async def update_self_invite_dict(self, guild, invite):
        if invite.inviter.id not in self.inviter_dict[guild.id]:
            self.inviter_dict[guild.id][invite.inviter.id] = {"total": invite.uses,
                                                              "name": f"{invite.inviter.name}#{invite.inviter.discriminator}",
                                                              "codes": {invite.code: invite.uses}}
        else:
            prev_uses = self.inviter_dict[guild.id][invite.inviter.id]["total"]
            prev_codes = self.inviter_dict[guild.id][invite.inviter.id]["codes"]
            inviter_name = self.inviter_dict[guild.id][invite.inviter.id]["name"]
            self.inviter_dict[guild.id][invite.inviter.id] = {"total": invite.uses + prev_uses,
                                                              "name": inviter_name,
                                                              "codes": {invite.code: invite.uses, **prev_codes}}


bot = bb(command_prefix=prefix, description=description, intents=intents)


def find_invite_by_code(invite_list, code):
    # Simply looping through each invite in an
    # invite list which we will get using guild.invites()
    for inv in invite_list:
        # Check if the invite code in this element
        # of the list is the one we're looking for
        if inv.code == code:
            # If it is, we return it.
            return inv
    return None


bot.remove_command("help")


@bot.command()
async def help(ctx, args=None):
    help_embed = discord.Embed(title=f"All commands from `[{prefix}] {bot.user.display_name}`",
                               colour=discord.Colour.random().value)
    command_names_list = [x.name for x in bot.commands]

    if not args:
        help_embed.set_thumbnail(url=str(bot.user.avatar_url))
        dictt = {}  # category:{name:,help:}
        x: discord.ext.commands
        for i, x in enumerate(bot.commands):
            if str(x.brief) in dictt:
                dictt[str(x.brief)].append({"name": x.name, "description": x.description})
            else:
                dictt[str(x.brief)] = [{"name": x.name, "description": x.description}]
        for category, commandss in dictt.items():
            help_embed.add_field(name=category if category != "None" else "Others/Misc",
                                 value="`" + ("`, `".join([c["name"] for c in commandss])) + "`")
        help_embed.add_field(
            name="Details",
            value=f"Type `{prefix}help <command name>` for more details about each command.",
            inline=False
        )

    # If the argument is a command, get the help text from that command:
    elif args in command_names_list:
        help_embed.title = "Command Information"
        command = bot.get_command(args)
        command_help = "" if isinstance(command.help, type(None)) else ("Help: " + command.help + "\n")
        command_desc = "" if (isinstance(command.description, type(None)) or command.description == "") else (
                "\nDescription: " + command.description)
        help_embed.add_field(
            name="Command name: `" + args + "`",
            value=command_help + "Usage: `" + prefix + args + " " + command.signature + "`" + command_desc
        )

    # If someone is just trolling:
    else:
        help_embed.add_field(
            name="Nope.",
            value="Don't think I got that command, boss!"
        )

    await ctx.send(embed=help_embed)


@bot.command(description="High low game, try to guess the correct number by clicking higher or lower.", brief="Game")
async def highlow(ctx):
    await highlow_game.run_highlowgame(ctx, bot)


@bot.command(description="Gets all animated emojis from this discord.", brief="None")
@commands.has_any_role("Admin (Discord)", "Mod (Discord)")
async def getemojis(ctx):
    emojis = await ctx.guild.fetch_emojis()
    for emoji in emojis:
        if emoji.animated:
            await ctx.message.add_reaction(emoji)
    await ctx.channel.send("added animated all emojis")


@bot.command(description="get countries played", brief="Admin Utility")
async def gettest(ctx: commands.Context):
    if ctx.author.id != 612861256189083669:
        await ctx.channel.send("no testing for u")
        return
    # await show_countries.getcountries(serverplayerupdates, ipaddress_access_key)
    await ctx.channel.send(len([m for m in ctx.guild.members if not m.bot]))


@bot.command(description="restart servers (admin only)", brief="Admin Utility")
@commands.has_role("Admin (Discord)")
async def restartserver(ctx: commands.Context, serverid: int, servercommand: str = "hubkick"):
    await console_commands.restartserver(ctx, serverid, servercommand)


@bot.command(description="get servers (admin only)", brief="Admin Utility")
@commands.has_role("Admin (Discord)")
async def getserver(ctx):
    await console_commands.getserver(ctx)


@bot.command(description="adds <:EMOJI:> to the desired <message_id> in [channel]. max 20 emojis per message",
             help="adds <:emoji:> to <message_id> in [channel]",
             brief="Hype")
@commands.has_any_role("Admin (Discord)", "Mod (Discord)")
async def addemoji(ctx, emoji: str, messageid: int, channel: discord.TextChannel = None):
    emojis = await ctx.guild.fetch_emojis()
    try:
        await ctx.message.delete(delay=3)
        if channel is None:
            msg = await ctx.fetch_message(messageid)
        else:
            msg = await channel.fetch_message(messageid)
        found = False
        for emoji_custom in emojis:
            if emoji[1:-1].lower() == emoji_custom.name.lower():
                await msg.add_reaction(emoji_custom)
                found = True
                await ctx.send(f"{emoji_custom} sent! Self destructing...", delete_after=3)
        if not found:
            await ctx.send("Emoji not found. Make sure to add the colons `:   :`", delete_after=3)
    except discord.NotFound:
        await ctx.send("Message id not found. Maybe message was deleted?", delete_after=3)


@bot.command(description="adds hype emojis",
             help="<message_id> <channel> <counts> (duration will be ~ counts*10 secs)", brief="Hype")
@commands.has_any_role("Admin (Discord)", "Mod (Discord)")
async def addhype(ctx, messageid: int, channel: discord.TextChannel = None, counts: int = 5):
    emojis = await ctx.guild.fetch_emojis()
    try:
        if channel is None:
            msg = await ctx.fetch_message(messageid)
        else:
            msg = await channel.fetch_message(messageid)
        total_emojis = 0
        await ctx.send(f"Hype sending! Self destructing...", delete_after=3)
        for emoji_custom in random.sample(emojis, k=len(emojis)):
            if emoji_custom.name.lower() in ["partyglasses", "pepoclap", "roll", "blob", "auke", "catdance", "pog",
                                             "hypertada", "feelsgoodman", "cata", "petangry",
                                             "typing", "petmelon", "petalex"]:
                total_emojis += 1
                await asyncio.sleep(random.randint(3, 3 + counts * 10))
                await msg.add_reaction(emoji_custom)
            if total_emojis > counts:
                break
    except discord.NotFound:
        await ctx.send("Message id not found. Maybe message was deleted?", delete_after=3)
    await ctx.message.delete(delay=3)


@bot.event
async def on_command_error(ctx: discord.ext.commands.Context, error: Exception, *args, **kwargs):
    print(ctx, str(error))
    if isinstance(type(error), discord.ext.commands.UserInputError):
        await ctx.message.channel.send("Wrong arguments: " + str(error))
    elif isinstance(error, discord.ext.commands.errors.BadArgument):
        await ctx.message.channel.send("Bad arguments: " + str(error))
    elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.message.channel.send("Missing argument: " + str(error))
    elif isinstance(error, discord.ext.commands.errors.CommandNotFound):
        await ctx.message.channel.send("ERROR: CommandNotFound")
    elif isinstance(error, discord.ext.commands.MissingRole):
        await ctx.channel.send("You dont have the permission to run this command.")
    else:
        await ctx.message.channel.send("Unknown error:" + str(type(error)) + str(error))


@bot.command(description="Play the guessing number game.", brief="Game")
async def guess(ctx: discord.ext.commands.Context):
    await ctx.channel.send('Guess a number between 1 and 1000000. Its one in a million')

    def is_correct(m):
        return m.author == ctx.author and m.content.isdigit() and m.channel == ctx.channel

    answer = random.randint(1, 1000000)
    print(answer)
    try:
        guess1 = await bot.wait_for('message', check=is_correct, timeout=20.0)
    except asyncio.TimeoutError:
        return await ctx.channel.send('Sorry, you took too long it was {}.'.format(answer))
    if int(guess1.content) > 1000000:
        await ctx.channel.send('Number too large, should be <1000000. Game ends.')
        return
    if int(guess1.content) == answer or False and ((ctx.author.id in [500744743660158987, 612861256189083669])
                                                   and random.randint(1, 10) > 5):
        await ctx.channel.send('You are right!!!!')
    else:
        await ctx.channel.send('Oops. It is actually {}.'.format(answer))


@bot.command(description="Check user's registered account's EXP", brief="Utility")
async def checkexp(ctx: discord.ext.commands.Context, user: discord.User = None):
    if prefix == "t?" and ctx.author.id != 612861256189083669:
        await ctx.channel.send("no testing for u")
        return
    if isinstance(user, type(None)):
        userTarget = ctx.author.id
    else:
        userTarget = user.id
    await ctx.channel.send('getting exp', delete_after=3)
    cursor = expgains.find({"duuid": userTarget})
    convertedexp_doc = convertedexp.find_one({"duuid": userTarget})
    if convertedexp_doc is None:
        convertedexp.insert_one({"duuid": userTarget, "converted": None})
    else:
        convertedexp_doc = convertedexp_doc["converted"]
    res = []
    for i, cur in enumerate(cursor):
        res.append(cur)
    if len(res) == 0:
        print("User has no EXP.")
        await ctx.channel.send("User has no EXP or user not found.")
    else:
        str_builder, exp_dict, convertedexp_doc = get_latest_exp(res, convertedexp_doc)
        if len(str_builder) > 0:
            convertedexp.find_one_and_replace({"duuid": userTarget},
                                              {"duuid": userTarget, "converted": convertedexp_doc})

            # todo count the amount of unconverted exp and trigger the next line if there is
            if len(str_builder) >= 1850:
                temp_str_builder = ""
                sent = False
                for i, strr in enumerate(str_builder.split("In Game Name: ")):
                    if i != 0:
                        temp_str_builder += "In Game Name: " + strr
                        sent = False
                        if i % 3 == 0:
                            await ctx.channel.send(temp_str_builder)
                            sent = True
                            temp_str_builder = ""
                if not sent:
                    await ctx.channel.send(temp_str_builder)
                await ctx.channel.send(f"\n Type `{prefix}convertexp` to convert your EXP into {ej.ax_emoji}."
                                       f"(You still can keep your EXP)")
            else:
                await ctx.channel.send(
                    str_builder + f"\n Type `{prefix}convertexp` to convert your EXP into {ej.ax_emoji}."
                                  f"(You still can keep your EXP)")
        else:
            await ctx.channel.send("You have no exp. ;-;")


@bot.command(description="Displays buyeffect menu.", brief="Utility")
async def buyeffect(ctx: discord.ext.commands.Context, peffect: str = None):
    if prefix == "t?" and ctx.author.id != 612861256189083669:
        await ctx.channel.send("t? is only for alex to test")
        return
    await ctx.channel.send("Fetching effects...", delete_after=2)
    effects_cost = {20: ["yellowDiamond", "yellowSquare", "yellowCircle"],
                    30: ["greenCircle", "whiteDoor", "yellowLargeDiam", "yellowSpark"],
                    50: ["whiteLancerRandom"], 80: ["whiteLancerRadius", "pixel", "bubble"],
                    200: ["rainbowPixel", "rainbowBubble"]}
    effects = [ee for c, e in effects_cost.items() for ee in e]
    owned_effects_collection = ingamecosmetics.find_one({"duuid": ctx.author.id})
    if owned_effects_collection is None:
        await ctx.channel.send("You need to have a **REGISTERED** mindustry account.")
        return
    owned_effects = owned_effects_collection["effects"]
    duuid = ctx.author.id
    if ax.find_one({"duuid": duuid}) is None:
        balance = 0
        ax.insert_one({"duuid": duuid, "ax": 0})
    else:
        balance = ax.find_one({"duuid": duuid})["ax"]
    if isinstance(peffect, type(None)):
        await effects_display.showeffectsmenu(ctx, effects_cost, owned_effects, effects, balance, ax, ingamecosmetics)
    else:
        await ctx.channel.send("Validating purchase...", delete_after=2)
        await effects_display.makepurchase(ctx, effects_cost, owned_effects, effects, peffect, ax, ingamecosmetics)


# todo show all effects?
#  @bot.command(description=f"Shows effects", brief="Utility")
# async def showeffects(ctx: discord.ext.commands.Context):
#     if prefix == "t?" and ctx.author.id != 612861256189083669:
#         msg: discord.Message = await ctx.channel.send("t? is only for alex to test")
#         await msg.add_reaction(ej.pog_emoji)
#         return
#     await effects_display.showeffectsmenu()


@bot.command(description=f"Check user's ranking in {ej.ax_emoji}", brief="Utility")
async def axleaderboard(ctx: discord.ext.commands.Context):
    await ctx.channel.send(f'for axleaderboard, type `a?axleaderboard`')


@bot.command(description=f"get image with user's pfp", brief="Utility")
async def getimage(ctx: discord.ext.commands.Context, user: discord.User):
    avatar = user.avatar_url_as(format="png",static_format="png",size=64)
    name = f"{user.name}#{user.discriminator}"
    image_data = await gen_image.getwelcomeimage(name=name,avatar=avatar)
    # emb = discord.Embed()
    await ctx.channel.send(file=image_data)


@bot.command(brief="Links", description="Shows the links to github.")
async def github(ctx: discord.ext.commands.Context):
    embed = discord.Embed(title=f"Github links", colour=discord.Colour.random().value)
    embed.add_field(name="watermelonbot (python)", value="https://github.com/alexpvpmindustry/watermelonbot",
                    inline=False)
    embed.add_field(name="lol bot (javascript)", value="https://github.com/unjown/unjownbot", inline=False)
    await ctx.channel.send(embed=embed)


@bot.command(description="Create giveaway.", brief="Admin Utility",
             help="<add/remove> <giveawaychannel> <anncchannel> <amount> <winners> <days> <hours> <'msg'>")
@commands.has_role("Admin (Discord)")
async def giveaway(ctx: discord.ext.commands.Context, what: str, channel: discord.TextChannel,
                   channelannc: discord.TextChannel, amount: int = 1,
                   winners: int = 0, days: int = 0, hours: int = 0, message: str = ""):
    cog: giveaway_bot.Giveaway = bot.get_cog("giveaway")
    if isinstance(cog, type(None)):
        bot.add_cog(giveaway_bot.Giveaway(bot))
        cog: giveaway_bot.Giveaway = bot.get_cog("giveaway")
        print("cog not started, started it")
    if what == "add":
        embed = giveaway_bot.form_msg_embed(message, amount, winners, days, hours * 3600, 0)
        msg = await channel.send(embed=embed)
        cog.addGiveawayEvent(msg.id, channel, channelannc, message, amount, winners, days, hours)
        await msg.add_reaction(ej.ax_emoji)
        await ctx.channel.send(f"giveaway added to {channel}. Giving {amount} {ej.ax_emoji} to {winners} people.")
    elif what.startswith("remove"):
        pass
    elif what == "findall":
        pass
    else:
        await ctx.channel.send("invalid command usage")


@bot.command(description=f"Convert user's exp into {ej.ax_emoji}.", brief="Utility")
async def convertexp(ctx: discord.ext.commands.Context):
    if prefix == "t?" and ctx.author.id != 612861256189083669:
        await ctx.channel.send("t? is only for alex to test")
        return
    await ctx.channel.send(f'Conversion rate: 1000 EXP -> 1 {ej.ax_emoji}. '
                           f'Minimum conversion = 1000 EXP.', delete_after=20)
    # add a new collection to show how much was claimed # add last claimed time.
    cursor = expgains.find({"duuid": ctx.author.id})
    convertedexp_doc = convertedexp.find_one({"duuid": ctx.author.id})
    if convertedexp_doc is None:
        convertedexp.insert_one({"duuid": ctx.author.id, "converted": None})
    else:
        convertedexp_doc = convertedexp_doc["converted"]
    res = []
    for i, cur in enumerate(cursor):
        res.append(cur)
    if len(res) == 0:
        await ctx.channel.send("User has no EXP or user not found. Can't convert emptiness.")
        return
    else:
        str_builder, exp_dict, convertedexp_doc = get_latest_exp(res, convertedexp_doc)
        if len(str_builder) > 0:
            new_Ax = 0
            for muuid, exps in exp_dict.items():
                for servdata in exps["servers"]:
                    rservername = servdata["servername"]
                    exp = servdata["exp"]
                    if exp is None:
                        exp = 0
                    claimed = servdata["claimed"]
                    if exp <0:
                        exp = 0
                        await ctx.channel.send("There is a bug here, PING alex. error 579")
                    if claimed <0:
                        claimed =0
                        await ctx.channel.send("There is a bug here, PING alex. error 580")
                    claims = (exp - claimed) // 1000  # integer division
                    if claims<0:
                        await ctx.channel.send("There is a bug here, PING alex. error 581")
                        claims=0
                    new_Ax += claims
                    servdata["claimed"] += claims * 1000
                    convertedexp_doc[muuid][rservername] = {"claimed": servdata["claimed"],
                                                            "lcdate": datetime.utcnow()}
            convertedexp.find_one_and_replace({"duuid": ctx.author.id},
                                              {"duuid": ctx.author.id, "converted": convertedexp_doc})
            if ax.find_one({"duuid": ctx.author.id}) is None:
                ax.insert_one({"duuid": ctx.author.id, "ax": new_Ax})
            else:
                ax.find_one_and_update({"duuid": ctx.author.id}, {"$inc": {"ax": new_Ax}})
            await ctx.channel.send(
                f"You have converted {new_Ax * 1000} EXP into {new_Ax} {ej.ax_emoji}.\nCongrats!. Type "
                f"`a?checkax @user` to check your current {ej.ax_emoji}.")
        else:
            await ctx.channel.send("You have no exp. ;-; Can't convert emptiness.")


@bot.command(description="For Appealing a member", brief="Utility",
             help="<minecraftBan|terrariaBan|mindustryKick|mindustryBan> <in_game_name> <reason>")
async def appeal(ctx: discord.ext.commands.Context, punishment: str, idoruuid: str, *, reason: str):
    if not punishment.startswith(("minecraftBan", "terrariaBan", "mindustryKick", "mindustryBan")):
        await ctx.channel.send("you must fill a punishment type:"
                               "\nmindustryBan, mindustryKick, terrariaBan, minecraftBan")
        return
    if isinstance(reason, type(None)) or reason == "":
        await ctx.channel.send("you must fill a reason of you got banned/kick")
        return
    await ctx.send("Thanks for appealing. Please be patient while our moderators attend to your appeal.")
    channel = bot.get_channel(791490149753683988)  # appeal-submission
    embed = discord.Embed(title="Appeal")
    embed.set_author(name=ctx.author.name + "#" + ctx.author.discriminator, icon_url=ctx.author.avatar_url)
    embed.add_field(name="Type:", value=str(punishment) + f" {ctx.author.mention}", inline=False)
    embed.add_field(name="In-game Player Name:", value=str(idoruuid), inline=False)
    embed.add_field(name="Reason:", value=str(reason), inline=False)
    await channel.send(embed=embed)


@bot.event
async def on_message(message: discord.Message):
    fig = "https://media.discordapp.net/attachments/785543837116399636/806563140116152380/reallyangrymelon.png"
    pepo_clap = "https://media.discordapp.net/attachments/799855760011427880/806869234122358794/792177151448973322.gif"
    if "<@!500744743660158987>" in message.content and prefix == "t?":
        await message.reply(fig, mention_author=True)
    elif message.content.startswith(prefix + "test"):
        await message.channel.send(f"this is to test stuff")
    elif (message.content.startswith(("ty", "Ty", "TY"))) and (bot.user in message.mentions):
        await message.reply("😊", mention_author=True)
    elif message.content == ':pepoclap:' and prefix == "t?":
        await message.reply(pepo_clap)
    elif prefix == "w?" and message.channel.id == 805105861450137600:  # counting hardcore channel
        if message.author.id != bot.user.id:
            await counting_bot.run_counterbot(message, bot)
    elif ("#alexcookie" in message.content) and (message.channel.id == 811993295114076190) and (prefix == "w?"):
        await cookiegame.triggercookieclaim(message, ax, bot)
    else:
        await bot.process_commands(message)


def runbot():
    with open("watermelon.config", "rb") as f:
        js = json.load(f)
        bot_token = js["bot_token"]
    # clientdisc = MyClient(intents=discord.Intents().all())
    # bot.load_extension("mastermelon.giveaway_bot2")
    bot.add_cog(giveaway_bot.Giveaway(bot))
    bot.run(bot_token)

#     elif message.content.startswith(prefix + "claimeffect"):
#         # todo @BOUNTY # check for role precondition then give effect
#         #  https://discordpy.readthedocs.io/en/latest/api.html#reaction
#         pass

import asyncio
import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import DiscordUtils

import artifact
import inventory
import helper
from keep_alive import keep_alive

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="?", intents=intents)

DOMAIN_FODDER = 21470 # Actual average is 10735

####################### Don't write code above here ##############################
"""
TODO List:
- actual exceptions
- character: preferred stat (atk, def, hp, em, er), role (dps, support1, support2, healer)
- artifact set effect
- equipping artifact on character
- character - artifact rating
- leaderboard for all characters
"""
####################### Don't write code above here ##############################

@bot.event
async def on_ready():
	activity = discord.Game(name="?help", type=10)
	await bot.change_presence(status=discord.Status.online, activity=activity)
	print("*** Artifact beta is online ***")

@bot.command(name="domain", 
			 brief="Run a domain. E.g: ?domain \"[domain name]\"",
			aliases=["d", "run"])
async def domain(ctx, domain_name):
	if inventory.get_capacity(ctx.author.id) >= 50:
		await ctx.reply("Inventory full.")
		return

	domain_name = artifact.domain_alias(domain_name)
	set = artifact.find_domain(domain_name.lower())
	if set == None:
		await ctx.reply("Invalid domain.")
		return
	reward = artifact.generate_domain_rewards(set)
	description = artifact.display_domain_rewards(reward)

	for r in reward:
		inventory.save_inventory_artifact(ctx.author.id, r)

	# Give fodder exp from doing domain
	inventory.add_fodder(ctx.author.id, DOMAIN_FODDER)

	# Create and send the embed
	embed=discord.Embed(title=domain_name.title(), 
						description=description, 
						color=0xF5A442)
	embed.set_author(name=ctx.author)

	# Get artifact image
	img = reward[0].image()
	if img != None:
		embed.set_thumbnail(url=img)

	# Repeat domain button
	repeat_button = Button(label="Repeat", style=discord.ButtonStyle.blurple)
	view = View(timeout=30)
	view.add_item(repeat_button)
	
	async def repeat_callback(interaction):
		if interaction.user.id == ctx.author.id:
			await interaction.response.edit_message(view=None)
			await domain(ctx, domain_name)
	repeat_button.callback = repeat_callback

	# Lock first artifact button
	lock_button = Button(label="Lock", style=discord.ButtonStyle.green)
	view.add_item(lock_button)
	
	async def lock_callback(interaction):
		if interaction.user.id == ctx.author.id:
			await interaction.response.defer()
			await fav(ctx, reward[0].id)
	lock_button.callback = lock_callback

	# Enhance first artifact button
	enhance_button = Button(label="Enhance", style=discord.ButtonStyle.danger)
	view.add_item(enhance_button)
	
	async def enhance_callback(interaction):
		if interaction.user.id == ctx.author.id:
			await interaction.response.defer()
			await enhance(ctx, reward[0].id)
	enhance_button.callback = enhance_callback

	# Fodder button
	fodder_button = Button(label="Fodder", style=discord.ButtonStyle.secondary)
	view.add_item(fodder_button)
	
	async def fodder_callback(interaction):
		if interaction.user.id == ctx.author.id:
			await interaction.response.defer()
			await fodder(ctx, reward[0].id)
	fodder_button.callback = fodder_callback
	
		
	await ctx.reply(embed=embed, view=view)

@bot.command(name="enhance", 
			 brief="Enhance an artifact. E.g: ?enhance [artifact id]",
			aliases=["e", "upgrade", "up"])
async def enhance(ctx, id):
	arti = inventory.find_artifact(id)
	if arti == None:
		await ctx.reply("Invalid artifact id.")
		return

	if not helper.is_authorised(id, ctx.author.id):
			await ctx.reply("Nice try, but you can't upgrade artifact " + id + " since it's not yours.")
			return
	
	up = arti.upgrade()
	if up == None:
		await ctx.reply("Artifact is already max level.")
		return
	if isinstance(up, int):
		await ctx.reply("Insufficient fodder. " + str(-1 * up) + " more fodder is required.")
		return

	fodder_exp = "{fodder_num:,}".format(fodder_num = inventory.get_fodder(ctx.author.id))
	# Create and send the embed
	embed=discord.Embed(title=up[0] + ": " + str(up[1]) + " → " + str(up[2]), 
						description="Fodder exp: " + fodder_exp + "\n\n" + arti.display_long(), 
						color=0x10FFB3)
	embed.set_author(name=ctx.author)

	# Get artifact image
	img = arti.image()
	if img != None:
		embed.set_thumbnail(url=img)

	# Repeat enhance button
	repeat_button = Button(label="Repeat", style=discord.ButtonStyle.blurple)
	view = View(timeout=30)
	view.add_item(repeat_button)
	
	async def repeat_callback(interaction):
		if interaction.user.id == ctx.author.id:
			await interaction.response.edit_message(view=None)
			await enhance(ctx, id)
	repeat_button.callback = repeat_callback

	# Fodder artifact button
	fodder_button = Button(label="Fodder", style=discord.ButtonStyle.green)
	view.add_item(fodder_button)
	
	async def fodder_callback(interaction):
		if interaction.user.id == ctx.author.id:
			await interaction.response.defer()
			await fodder(ctx, id)
	fodder_button.callback = fodder_callback

	
	await ctx.reply(embed=embed, view=view)

@bot.command(name="inventory", 
			 brief="Optional filters: max/unmax/lock/unlock/sandbox/reroll",
			aliases=["i", "inv"])
async def inv(ctx, filter=None):
	artifact_list = inventory.display_inventory(ctx.author.id, filter)
	embeds = helper.create_embed_page(ctx.author.name, ctx.author.id, filter, artifact_list)
	for embed in embeds:
		embed.set_thumbnail(url=ctx.author.display_avatar.url)
	
	paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx)
	paginator.add_reaction('⏮️', "first")
	paginator.add_reaction('⬅️', "back")
	paginator.add_reaction('➡️', "next")
	paginator.add_reaction('⏭️', "last")
	await paginator.run(embeds)

@bot.command(name="lock", 
			 brief="Lock/unlock an artifact. E.g: ?lock \"[artifact1 id, artifact2 id]\"",
			aliases=["l", "favouite", "fav"])
async def fav(ctx, id):
	id_list = helper.parse_into_list(str(id))
	
	if len(id_list) == 1:
		# Single artifact
		arti = inventory.find_artifact(id)
		if arti == None:
			await ctx.reply("Invalid artifact id.")
			return
		
		if not helper.is_authorised(id, ctx.author.id):
				await ctx.reply("In your dreams. You can't lock artifact " + id + " since it's not yours.")
				return
	
		is_fav = arti.toggle_favourite()
		if is_fav:
			await ctx.reply("You have locked artifact " + str(id) + ".")
		else:
			await ctx.reply("You have unlocked artifact " + str(id) + ".")

		return

	# Multiple artifact
	# Loop through each artifact id and lock them if they exist/they're owner
	locked = []
	for item in id_list:
		if not helper.is_authorised(item, ctx.author.id):
			continue
		
		arti = inventory.find_artifact(int(item))		
		if arti != None:
			locked.append(item)
			arti.toggle_favourite()

	# Indicate which artifacts are foddered and how much exp
	if len(locked) == 0:
			await ctx.reply("In your dreams. You can't lock these artifacts because it's not yours.")
	else:
		await ctx.reply("Successfully locked or unlocked these artifacts: " + ", ".join(locked) + ".")
	


@bot.command(name="fodder", 
			 brief="Fodder artifacts. E.g: ?fodder \"[artifact1 id, artifact2 id]\"",
			aliases= ["f", "trash"])
async def fodder(ctx, id):
	id = str(id)
	
	# Fodder all
	if id.lower() == "all":
		inventory.fodder_all(ctx.author.id)
		fodder = "{fodder_num:,}".format(fodder_num = inventory.get_fodder(ctx.author.id))
		await ctx.reply("All unlocked artifacts have been foddered. Currently you have " + fodder + " fodder exp.")
		return
		
	# Fodder specified
	id_list = helper.parse_into_list(id)

	# Loop through each artifact id and fodder them if they exist/they're owner/not locked
	foddered = []
	for item in id_list:
		if not helper.is_authorised(item, ctx.author.id):
			continue
		
		arti = inventory.find_artifact(int(item))		
		if arti != None and not arti.favourite:
			foddered.append(item)
			arti.fodder(ctx.author.id)

	# Indicate which artifacts are foddered and how much exp
	if len(foddered) == 0:
			await ctx.reply("Fodder failed.")
	else:
		fodder = "{fodder_num:,}".format(fodder_num = inventory.get_fodder(ctx.author.id))
		await ctx.reply("Successfully foddered these artifacts: " + ", ".join(foddered) + ". Currently you have " + fodder + " fodder exp.")

@bot.command(name="view", 
			 brief="View artifact. E.g: ?view [artifact id]",
			aliases=["v"])
async def view(ctx, id):
	arti = inventory.find_artifact(id)
	if arti == None:
		await ctx.reply("Invalid artifact id.")
		return

	owner = await bot.fetch_user(inventory.get_owner(id))
	embed=discord.Embed(title="Viewing " + owner.name + "'s' Artifact", 
						description=arti.display_long(), 
						color=0x45DAFF)
	embed.set_author(name=ctx.author)
	
	# Get artifact image
	img = arti.image()
	if img != None:
		embed.set_thumbnail(url=img)

	# Enhance button
	enhance_button = Button(label="Enhance", style=discord.ButtonStyle.blurple)
	view = View(timeout=30)
	view.add_item(enhance_button)
	
	async def enhance_callback(interaction):
		if interaction.user.id == ctx.author.id:
			await interaction.response.edit_message(view=None)
			await enhance(ctx, id)
	enhance_button.callback = enhance_callback

	# Fodder button
	fodder_button = Button(label="Fodder", style=discord.ButtonStyle.green)
	view.add_item(fodder_button)
	
	async def fodder_callback(interaction):
		if interaction.user.id == ctx.author.id:
			await interaction.response.edit_message(view=None)
			await fodder(ctx, id)
	fodder_button.callback = fodder_callback

	# Lock button
	lock_button = Button(label="Lock", style=discord.ButtonStyle.danger)
	view.add_item(lock_button)
	
	async def lock_callback(interaction):
		if interaction.user.id == ctx.author.id:
			await interaction.response.defer()
			await fav(ctx, id)
	lock_button.callback = lock_callback
	
	await ctx.reply(embed=embed, view=view)

@bot.command(name="sandbox", 
			 brief="Create custom artifact.",
			 description="E.g: ?sandbox \"[set]\" [type] [mainstat] [substat1] ...",
			aliases=["s", "custom"])
async def sandbox_mode(ctx, set, type, mainstat, substat1, substat2, substat3, substat4=None):
	custom = artifact.custom_artifact(set, type, mainstat, [substat1, substat2, substat3, substat4])
	if isinstance(custom, str):
		await ctx.reply(custom)
		return
	inventory.save_inventory_artifact(ctx.author.id, custom)

	# Create and send the embed
	embed=discord.Embed(title=ctx.author.name + "'s Custom Artifact", 
						description=custom.display_long(), 
						color=0xF5A442)
	embed.set_author(name=ctx.author)

	# Get artifact image
	img = custom.image()
	if img != None:
		embed.set_thumbnail(url=img)
		
	await ctx.reply(embed=embed)

@bot.command(name="reroll", 
			 brief="Reroll a substat. E.g: ?reroll [artifact id] [substat]",
			aliases=["r"])
async def reroll_mode(ctx, id, substat):
	arti = inventory.find_artifact(id)
	if arti == None:
		await ctx.reply("Invalid artifact id.")
		return

	if arti.sandbox:
		await ctx.reply("Cannot reroll sandbox artifacts.")
		return

	if not helper.is_authorised(id, ctx.author.id):
		await ctx.reply("Nice try but you can't reroll artifact " + id + " since it's not yours.")
		return
	
	new_substat = arti.reroll_substat(ctx.author.id, substat)
	if new_substat == None:
		await ctx.reply("Invalid substat.")
		return
	if new_substat == "max":
		await ctx.reply("Already at max amount of rerolls for this artifact.")
		return

	embed=discord.Embed(title="New Substat: " + new_substat[0], 
						description=arti.display_long(), 
						color=0x10FFB3)
	embed.set_author(name=ctx.author)
	
	# Get artifact image
	img = arti.image()
	if img != None:
		embed.set_thumbnail(url=img)
	
	await ctx.reply(embed=embed)

@bot.command(name="admin", 
			 brief="Admin purposes only.")
async def admin_commands(ctx, command, id, amount=None):
	if ctx.author.id not in helper.read_file("config.json")["admin"]:
		await ctx.reply("You are not authorised to use this command.")
		return

	if command == "give":
		# Give fodder exp
		inventory.add_fodder(id, int(amount))
		receiver = await bot.fetch_user(id)
		await ctx.reply(amount + " fodder exp given to " + receiver.name)

	if command == "sandbox":
		# Turn off sandbox attribute
		arti = inventory.find_artifact(id)
		arti.sandbox = False
		inventory.update_artifact(id, arti)
		await ctx.reply("Artifact " + id + " has exited dream Vanarana.")
		return None

	if command == "reroll":
		# Reset reroll attribute
		arti = inventory.find_artifact(id)
		arti.rerolled = 0
		inventory.update_artifact(id, arti)
		await ctx.reply("Artifact " + id + "'s reroll amount has been reset.")

@bot.command(name="faq", 
			 brief="Additional help for this bot.")
async def faq(ctx):
	guide = '''
**What does S and R in front of artifact id mean?**
S indicates that the artifact is made using sandbox mode. R indicates the artifact has been rerolled at least once.

**What domains are available?**
- Boss: gladiator (GF), wanderer (WT)
- City of gold: desert pavilion (DPC), paradise lost (FoPL)
- Clear pool and mountain cavern: bloodstained (BC), noblesse (NO)
- Domain of guyun: bolide (RB), archaic petra (AP)
- Hidden palace of zhou formula: crimson witch (CWoF), lavawalker (LW)
- Midsummer courtyard: thundering fury (TF), thundersoother (TS)
- Momiji-dyed court: emblem (EoSF), shimenawa (SR)
- Peak of vindagnyr: blizzard (BS), heart of depth (HoD)
- Ridge Watch: tenacity (TotM), pale flame (PF)
- Slumbering court: husk (HoOD), clam (OC)
- Spire of solitary enlightenment: deepwood (DM), gilded dreams (GD)
- Valley of remembrance: viridescent (VV), maiden (MB)

**How many times can I reroll? **
Currently you can reroll 4 times per artifact. You will get deducted fodder exp depending on the level of the artifact (subject to change). 

**How to get more fodder exp?**
Use the fodder command on your artifacts or run more domains.

**My inventory got cleared.**
Because this bot is in development, inventory are subject to be cleared anytime.

**What is the sandbox command?**
Use it to create a custom artifact (such as one you have in Genshin) so you can try testing your luck when enhancing it. 

**The bot didn't respond to my command.**
Either you found a bug, the bot got rate limited or you didn't put multi-word arguments in quotations. E.g. ?domain "valley of remembrance" will work. 

**How accurate are the rates? (Why do I keep getting double DEF?)**
The rates for mainstat and substat are very close to that of Genshin. All substats have equal chance of getting enhanced. RNG just seems to like DEF more.

**Who do I message if I have a question or feedback?**
꒒ꍟꈤ ꀘꉄꈤ#2578
	'''
	await ctx.reply(guide)

##### THINGS TO RUN THE BOT ##########
keep_alive()
token = os.environ.get("TOKEN")
bot.run(token)
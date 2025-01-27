from __future__ import annotations
import discord
from myModal import MyModal
import uuid
import time
from modMenu import ConsequenceActionButtons, ConsequenceActionButtonsAutoBanned, ConsequenceActionButtonsAutoKicked
from ticket import Ticket, tickets, Interaction, Button

# =========== TYPE ALIASES ==============
Interaction = discord.Interaction
Button = discord.ui.Button
# ========= END TYPE ALIASES ===========

def get_drop_down_options(elems : dict[str, str]) -> list[discord.SelectOption]:
        return [discord.SelectOption(label=l, description=d) for l, d in elems.items()]

async def send_completionEmbed(interaction, bot, tid, embeds=None, autoBanned=False, autoKicked=False):
    embeds  = embeds if embeds else []
    mod_channel = bot.mod_channels[bot.guilds[0].id]

    if interaction:
        await interaction.followup.send(embeds=[await create_completionEmbed(bot, tid)], ephemeral=True)
    if embeds is None or len(embeds) == 0:
        mod_channel = bot.mod_channels[bot.guilds[0].id]
        embed = await create_completionEmbed(bot, tid)
        embed.title = f"** Report Ticket ID: {tid} **"
        
        if tickets[tid].sextortion_content == "Content includes explicit images":
                explicit_warning = str("""```css\n**[Explicit Warning!]** \nThis content is explicit! Please act with caution.```""")
                embed.description = explicit_warning
                embed.color = discord.Color.red()
        embeds.append(embed) # Ensure that the context embed is displayed when a user blocks/not

    nextMessageDescript = '### Please proceed by choosing action toward reported user.'
    if autoBanned == True:
        nextMessageDescript += " (Note that this user was automatically banned for this message.)"
    elif autoKicked == True:
        nextMessageDescript += " (Note that this user was automatically kicked for this message.)"
    next_step_embed = discord.Embed(title = ' **__Next Steps__**', description=nextMessageDescript)
    disapproveLabelText = 'Dismiss the report and take no action against the user.'
    if autoBanned == True:
          disapproveLabelText += " The user will be unbanned."
    next_step_embed.add_field(name='Disapprove User Label', value=disapproveLabelText, inline=False)
    if autoBanned == False:
        next_step_embed.add_field(name='Ban User', value='User and associated IP will be permanently removed from guild.', inline=False)
        if autoKicked == False:
                next_step_embed.add_field(name='Kick User', value='User will be removed from guild/channel and can only rejoin by invite.', inline=False)
        next_step_embed.add_field(name='Warn User', value='User will be warned of their behavior. If this is a re-offense, the user will be kicked.', inline=False)
    embeds.append(next_step_embed)
    if autoBanned:
        await mod_channel.send(embeds=embeds, view=ConsequenceActionButtonsAutoBanned(bot, tid))
        await tickets[tid].bot_msg.delete()
    elif autoKicked:
        await mod_channel.send(embeds=embeds, view=ConsequenceActionButtonsAutoKicked(bot, tid))  
    else:
        await mod_channel.send(embeds=embeds, view=ConsequenceActionButtons(bot, tid))


async def create_completionEmbed(bot, tid):
    embed = CompletionEmbed(bot, tid)
    if tickets[tid].message_link != "":
        # link = 'https://discord.com/channels/1103033282779676743/1103033287250804838/1109919564701126787'
        try:
            link = tickets[tid].message_link.split('/')
            if tickets[tid].type == 'Manual':
                message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(int(link[-1]))
                tickets[tid].message = message.content
                tickets[tid].msg_user_id = message.author
                
            link = tickets[tid].message_link.split('/')
            message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(int(link[-1]))
            tickets[tid].message = message.content
            tickets[tid].msg_user_id = message.author
        except:
            tickets[tid].message = 'Could not identify.'


    for key, value in tickets[tid]:
        # print(key, value)
        if key in ['status', 'type', 'bot_msg']:
                continue
        embed.add_field(name=key, value=value)
    
    return embed

async def create_BlockingHelpEmbed(bot, tid):
    embed = discord.Embed(title='__Instruction on How to Block User__', \
                          description='_If you would like to block this user, \
                                please refer to the information in the link above._ \
                                        ', \
                                                url='https://support.discord.com/hc/en-us/articles/217916488-Blocking-Privacy-Settings-#:~:text=In%20your%20DM%20chat%2C%20clicking,let%20you%20block%20the%20user.')
    
    return embed

async def response_message(word : str, interaction : Interaction):
        await interaction.response.send_message(f'You responded: {word}', ephemeral=True)

class CompletionEmbed(discord.Embed):
    def __init__(self, bot, tid : int):
        super().__init__()
        self.tid = tid
        self.bot = bot
        self.title = 'Summary of Report Request'
        self.description = \
                '"Thank you. We will investigate further. \
                Please expect a response within the next 36 hours."'
        self.add_field(name='Ticket ID', value=tid)
        self.add_field(name='Ticket Type', value=tickets[tid].type, inline=False)
        self.add_field(name='Status', value='In Progress', inline=False)
        tickets[tid].status = 'In Progress'

"""
Prompt: "Please select reason for reporting this content"
"""
class ReportSelection(discord.ui.View): 
    def __init__(self, bot, tid):
        super().__init__()
        self.bot = bot
        self.tid = tid
    
    @discord.ui.select(placeholder='Please select reason for reporting this content', \
        options=get_drop_down_options({
                'Harassment'         : 'User is repetitively making unwanted contact and sending threatening or unuwanted sexual messages.',
                'Spam'               : 'Message promotes suspicious or fraudulent activity',
                'Offensive Content'  : 'Displays disturbing content',
                'Imminent Danger'    : 'Threatening self-harm or harm to others',
                'Other'              : 'Unlisted abusive behavior'
        })
    )
    async def selection_callback(self, interaction : Interaction, selection : discord.ui.Select):
        # await interaction.response.send_message(f'You chose {selection.values[0]}',  ephemeral=True)
        tickets.update({self.tid : Ticket()})
        tickets[self.tid].user_id_requester = interaction.user
        tickets[self.tid].reason = selection.values[0]
        reason = ExplanationModal(selection.values[0], self.tid)
        await interaction.response.send_modal(reason)
        await reason.wait()
        time.sleep(1)

        if selection.values[0] == 'Harassment':
            await interaction.followup.send("You selected: Harassment", view=HarassmentSelection(self.bot, self.tid), ephemeral=True)
        else:
            await interaction.followup.send("Would you like to block this user?",
                view=blockUserSelection(self.bot, self.tid), ephemeral=True)


class ExplanationModal(discord.ui.Modal):
    def __init__(self, choice, tid):
        super().__init__(title=f"Your report reasoning is: {choice}")
        self.tid = tid

        self.add_item(discord.ui.TextInput(label="Paste Message Link ", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="Please explain your reasoning", style=discord.TextStyle.long))

    async def on_submit(self, interaction: discord.Interaction):
        tickets[self.tid].message_link = self.children[0].value
        tickets[self.tid].reason = self.children[1].value
        await interaction.response.send_message("Thank you for your response!", ephemeral=True)
        self.stop()
"""
Prompt: Harassment: Select Type
"""
class HarassmentSelection(discord.ui.View):
    def __init__(self, bot, tid):
        super().__init__()
        self.tid = tid
        self.bot = bot

    @discord.ui.select(placeholder='Select Type',
         options=get_drop_down_options({
            'Sextortion'                : 'The user is threatening to spread or has spread sexually explicit images.',
            'Hate Speech'               : 'Targeted attack toward a group or individual',
            'Encouraging Self-harm'     : 'Prompting other user to harm themselves',
            'Threats'                   : 'User is threatening violence or doxxing',
            'Other'                     : 'Abuse type not listed'
        })
    )
    async def selection_callback(self, interaction : Interaction, selection:discord.ui.Select):
        tickets[self.tid].harassment_type = selection.values[0]

        await response_message(selection.values[0], interaction)

        if selection.values[0] == 'Sextortion':
            await interaction.followup.send(view=SextortionTypeSelection(self.bot, self.tid),
                    ephemeral=True)
        else:
            await interaction.followup.send("Is this the first time you've seen abusive content from this user?",
                view=previouslySeenSelection(self.bot, self.tid), ephemeral=True)


def BinaryOption(label_1 : str, label_2 : str):
        class Impl(discord.ui.View):
                def __init__(self, bot, tid : int, opt_1 : callable, opt_2 : callable):
                        super().__init__()
                        self.tid = tid
                        self.bot = bot
                        self.opt_1 = opt_1
                        self.opt_2 = opt_2

                @discord.ui.button(label=label_1, style=discord.ButtonStyle.red)
                async def Opt1Button(self, interaction : Interaction, button : Button):
                        await self.opt_1(self.bot, self.tid, interaction, button)

                @discord.ui.button(label=label_2, style=discord.ButtonStyle.red)
                async def Opt2Button(self, interaction : Interaction, button : Button):
                        await self.opt_2(self.bot, self.tid, interaction, button)

        return Impl

# =========== TYPE ALIASES ==============
YesNoOption = BinaryOption("Yes", "No")
# ========= END TYPE ALIASES ===========

"""
Prompt: Sextortion - Select Type of Content
"""
class SextortionTypeSelection(discord.ui.View):
    def __init__(self, bot, tid):
        super().__init__()
        self.tid = tid
        self.bot = bot

    @discord.ui.select(placeholder='Select Type of Content', options=get_drop_down_options({
            'Content includes explicit images'                  : 'Depicts sexually explicit imagery',
            'Content is a threat to spread explicit images'     : 'Threatening to send or post explicit images of another individual',
        })
    )
    async def sextortype_callback(self, interaction : Interaction, selection:discord.ui.Select):
        tickets[self.tid].sextortion_content = selection.values[0]
        await response_message(selection.values[0], interaction)
        await interaction.followup.send('Do you personally know the user responsible?',
                # 'Are these images of you or someone else?',
                view=UserResponsibleSelection(self.bot, self.tid), ephemeral=True)
                # view=ImageOwnerSelection(self.bot, self.tid), ephemeral=True)

async def ImageOwnerCallback1(bot, tid : int, interaction : Interaction, button : Button):
        tickets[tid].image_owner = 'Me'
        await response_message(button.label, interaction)
        await interaction.followup.send("Have you shared explicit images with this user?",
                view=SharedExplicitSelection(bot, tid), ephemeral=True)

async def ImageOwnerCallback2(bot, tid : int, interaction : Interaction, button : Button):
        tickets[tid].image_owner = 'Other'
        await response_message(button.label, interaction)
        await interaction.followup.send("Do you know this other person?", 
        view=KnowOtherSelection(bot, tid), ephemeral=True)

"""
Prompt: Are these images of you or someone else?
"""
def ImageOwnerSelection(bot, tid : int):
        return BinaryOption("Me", "Other")(bot, tid, ImageOwnerCallback1, ImageOwnerCallback2)

async def owner_choice_callback(bot, tid : int, interaction : Interaction, button : Button):
        await response_message(button.label, interaction)
        await interaction.followup.send("Are these images of you or someone else?",
                view=ImageOwnerSelection(bot, tid), ephemeral=True)
        tickets[tid].know_responsible = button.label

"""
Prompt: Do you know this other person?
"""
def UserResponsibleSelection(bot, tid : int):
        return YesNoOption(bot, tid, owner_choice_callback, owner_choice_callback)

async def shared_explicit_warning(interaction : Interaction):
        await interaction.followup.send("If you have not provided images to this user, it is possible they may be lying and trying to extort you. You may also have been hacked.", ephemeral=True)

async def my_images_callback(bot, tid : int, interaction : Interaction, button : Button):
        tickets[tid].shared_explicit = 'Yes'
        await response_message("Yes.", interaction)
        await shared_explicit_warning(interaction)
        await interaction.followup.send("Do you know what images this user has?",
                view=KnowImageSelection(bot, tid), ephemeral=True)

async def others_images_callback(bot, tid : int, interaction : Interaction, button : Button):
        tickets[tid].shared_explicit = 'No'
        # await interaction.response.send_message(embed=await create_completionEmbed(self.bot, self.tid), ephemeral=True)
        await response_message("No.", interaction)
        await shared_explicit_warning(interaction)
        await interaction.followup.send("Would you like to block this user?",
                view=blockUserSelection(bot, tid), ephemeral=True)

"""
Prompt: "Have you shared explicit images with this user?"
"""
def SharedExplicitSelection(bot, tid : int):
        return YesNoOption(bot, tid, my_images_callback, others_images_callback)

async def know_image_callback(bot, tid : int, interaction:Interaction, button:Button):
        tickets[tid].know_image = button.label
        await interaction.followup.send("Would you like to block this user?",
                view=blockUserSelection(bot, tid), ephemeral=True)

async def handle_know_image(bot, tid : int, interaction : Interaction, button : Button):
        # await response_message("Yes.", interaction)
        await interaction.response.send_message('You responded: Yes.', embed=ImageRemovalEmbed(), ephemeral=True)
        time.sleep(5)
        await know_image_callback(bot, tid, interaction, button)

async def handle_dont_know_image(bot, tid : int, interaction : Interaction, button : Button):
        await response_message("No.", interaction)
        await know_image_callback(bot, tid, interaction, button)

"""
Prompt: "Do you know what images this user has?"
"""
def KnowImageSelection(bot, tid : int):
        return YesNoOption(bot, tid, handle_know_image, handle_dont_know_image)

async def know_other_choice_callback(bot, tid : int, interaction:Interaction, button:Button):
        await interaction.followup.send("Did the user post an explicit image?",
                view=PostExplicitSelection(bot, tid), ephemeral=True)
        tickets[tid].know_other = button.label

async def handle_know_other(bot, tid : int, interaction : Interaction, button : Button):
        UsernameModal = UsernameInputModal(tid)
        await interaction.response.send_modal(UsernameModal)
        await UsernameModal.wait()
        await know_other_choice_callback(bot, tid, interaction, button)

async def handle_dont_know_other(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message("You responded: No.", ephemeral=True)
        await know_other_choice_callback(bot, tid, interaction, button)
        
"""
Prompt: "Do you know this other person?"
"""
def KnowOtherSelection(bot, tid : int):
        return YesNoOption(bot, tid, handle_know_other, handle_dont_know_other)

"""
Prompt: "Do you know this other person?" > "Yes" > "Enter Username"
"""
class UsernameInputModal(discord.ui.Modal, title='Enter Username'):
    def __init__(self, tid):
        super().__init__()
        self.tid = tid

        self.value = None

        self.add_item(discord.ui.TextInput(label="Username", style=discord.TextStyle.short))

    async def on_submit(self, interaction: Interaction):
        tickets[self.tid].other_username = self.children[0].value
        await interaction.response.send_message("Thank you for filling out the form!", ephemeral=True)
        self.stop()

async def post_explicit_callback(bot, tid : int, interaction : Interaction, button : Button):
        tickets[tid].post_explicit = button.label # was previously doing this after awaiting, moved before
        await interaction.followup.send("Would you like to block this user?",
                view=blockUserSelection(bot, tid), ephemeral=True)

async def handle_post_explicit(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message('You responded: Yes.', embed=ImageRemovalEmbed(),
                ephemeral=True)
        await post_explicit_callback(bot, tid, interaction, button)

async def handle_didnt_post_explicit(bot, tid : int, interaction : Interaction, button : Button):
        await response_message("No.", interaction)
        await post_explicit_callback(bot, tid, interaction, button)

"""
Prompt: "Did the user post an explicit image?"
"""
def PostExplicitSelection(bot, tid : int):
        return YesNoOption(bot, tid, handle_post_explicit, handle_didnt_post_explicit)

"""
Embed to redirect to takeitdown or other external image removal resources
"""
class ImageRemovalEmbed(discord.Embed):
    def __init__(self):
        super().__init__(title='Removal/Prevention Resources', url='https://takeitdown.ncmec.org/')
        self.add_field(name="Please click on the link above.", value="These instructions will help get your image removed and stop their spread", inline=False)

"""
Prompt: Is this the first time you've seen abusive content from this user?
"""
def previouslySeenSelection(bot, tid: int):
      return YesNoOption(bot, tid, handle_prev_seen, handle_no_prev_seen)

async def handle_prev_seen(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message("Would you like to block this user?",
                view=blockUserSelection(bot, tid), ephemeral=True)

async def handle_no_prev_seen(bot, tid : int, interaction : Interaction, button : Button):
        await interaction.response.send_message("Would you like to block this user?",
                view=blockUserSelection(bot, tid), ephemeral=True)

"""
Embed to more elegantly display block URL
"""
class newBlockEmbed(discord.Embed):
    def __init__(self):
        super().__init__(title='Blocking a User', url='https://support.discord.com/hc/en-us/articles/217916488-Blocking-Privacy-Settings-#:~:text=In%20your%20DM%20chat%2C%20clicking,let%20you%20block%20the%20user')

"""
Prompt: "Would you like to block this user?"
"""
def blockUserSelection(bot, tid: int):
      return YesNoOption(bot, tid, handle_block_user, handle_dont_block_user)

async def handle_block_user(bot, tid : int, interaction : Interaction, button : Button):
        link = tickets[tid].message_link.split('/')
        offendingMessage = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(int(link[-1]))
        username = offendingMessage.author.display_name
        blockMessage = username + " has been blocked."
        await interaction.response.send_message(blockMessage, ephemeral=True)
        await send_completionEmbed(interaction, bot, tid)

async def handle_dont_block_user(bot, tid : int, interaction : Interaction, button : Button):
        instructions = "If you later decide you want to block this user, refer to the link below for detailed instructions."
        await interaction.response.send_message(instructions, ephemeral=True, embed=newBlockEmbed())
        await send_completionEmbed(interaction, bot, tid)

class MainMenuEmbed(discord.Embed):
    def __init__(self):
        super().__init__()
        self.title = "Main Menu Report"
        self.description = "This is the information for the Main Menu"
        self.add_field(name="Report", value="Click this to report", inline=False)
        self.add_field(name="Help", value="Click this to receive more information", inline=False)
        self.add_field(name="Talk to Moderator", value="Click this to request a private conversation with a moderator", inline=False)

class MainMenuButtons(discord.ui.View):
    def __init__(self, bot, mod_channel):
        super().__init__()
        self.bot = bot
        self.mod_channel = mod_channel
        self.add_item(Button(label='Help', style=discord.ButtonStyle.link, url='https://www.stopsextortion.com/get-help/'))

    @discord.ui.button(label="Report", style=discord.ButtonStyle.red)
    async def reportBtn(self, interaction: Interaction, button:Button):
        # await interaction.response.send_modal(MyModal())
        tid = uuid.uuid4()
        await interaction.response.send_message(view=ReportSelection(self.bot, tid), ephemeral=True)
    
    # @discord.ui.button(label="Help", style=discord.ButtonStyle.red)
    # async def helpBtn(self, interaction: Interaction, button:Button):
    #     await self.mod_channel.send(f'Forwarded message:\n{interaction.user.display_name}: Help!')
    #     await interaction.response.send_message("You clicked the help button. We've sent your request to the mod-team", ephemeral=True)

    @discord.ui.button(label="Talk to Mod", style=discord.ButtonStyle.red)
    async def talkBtn(self, interaction: Interaction, button:Button):
        await self.mod_channel.send(f'Forwarded message:\n{interaction.user.display_name}: Help!')
        await interaction.response.send_message("You clicked the talk to mod button. We've sent your request to the mod-team", ephemeral=True)

	# async def reportBtn(self, interaction: Interaction, button:Button):
    #     await interaction.response.send_modal(MyModal())
    

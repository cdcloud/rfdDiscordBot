import boto3
from boto3.dynamodb.conditions import Key, Attr
import datetime
import discord
from discord.ext.commands import Bot
from discord.ext import commands
import json
import asyncio
import time

Client = discord.Client()
client = commands.Bot(command_prefix="!")

session = boto3.Session(profile_name="dclouddev")

dynamodb = session.resource('dynamodb')

char_table = dynamodb.Table('rfdCharacters')
att_table = dynamodb.Table('rfdAttendance')

@client.event
async def on_ready():
    print("Bot is Ready!")

@client.event
async def on_message(message):
    if message.content.lower().startswith("!rfdhelp"):
        reply = "```++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n" \
                "Commands currently available for the Roll for Fall Damage Bot:\n" \
                "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n" \
                "!attend(!attendance) <MM/DD> (Support for year coming soon)\n" \
                "!late <character name> <MM/DD> <reason>\n" \
                "!absent <character name> <MM/DD> <reason>\n" \
                "!character save <character name> <server-server>\n" \
                "!character view\n" \
                "!count (Officers only)\n" \
                "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++```"
        await client.send_message(message.channel, reply)

    if message.content.lower().startswith("!attendance") or message.content.lower().startswith("!attend"):
        args = message.content.split(" ")
        if len(args) == 2:
            if args[1].eq("reset"):
                print("Reset")
            date = args[1].split("/")
            if int(date[0]) <= 12 and int(date[1]) <= 31:
                year = datetime.datetime.now().year
                args[1] += "/%s" % year
                response = att_table.query(
                    KeyConditionExpression=Key('date').eq(args[1]) & Key('active').eq(True)
                )
                reply = "```++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n" \
                        "+ Date       + Initiated By + Character    + Status + Reason                   +\n" \
                        "+------------------------------------------------------------------------------+\n"
                for item in response["Items"]:
                    char_name = "{:<12}".format(item["character_name"])
                    reason = "{:<24}".format(item["reason"])
                    discord_user = item["discord_user"]
                    att_date = "{:<10}".format(item["date"])
                    status = "{:<6}".format(item["status"])
                    reply += "+ %s + %s + %s + %s + %s +\n" % (att_date, discord_user, char_name, status, reason)
                reply += "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++```"
                await client.send_message(message.channel, reply)
            else:
                await client.send_message(message.channel, "Invalid Date format. Please use MM/DD for date")
        # TODO Add active field to db for all rows to control "deletion"
        if len(args) == 3:
            if args[2].lower().eq("all"):
                if message.author.id == "208298739679494144" or "430057708759023626" in [role.id for role in message.author.roles]:
                    print("Reset All")
                else:
                    print("You do not have permission to run this command")
            else:
                print("Reset %s") % str(args[2])

    # !late <character> <date> <reason>
    if message.content.lower().startswith("!late"):
        args = message.content.split(" ")
        user = message.author
        userid = message.author.id
        if len(args) >= 3:
            # Crude date validator
            date = args[2].split("/")
            if int(date[0]) <= 12 and int(date[1]) <= 31:
                year = datetime.datetime.now().year
                args[2] += "/%s" % year
                await client.send_message(message.channel, "<@%s> says %s will be late on %s." % (userid, args[1], args[2]))
                reason = " ".join(args[3:]) if len(args) >= 4 else "Personal Reasons"
                att_table.put_item(
                    Item={
                        'discord_user': str(user),
                        'character_name': args[1],
                        'status': "Late",
                        'date': args[2],
                        'reason': reason,
                        'active': True
                    }
                )
            else:
                await client.send_message(message.channel, "Invalid Date format. Please use MM/DD for date")

    if message.content.lower().startswith("!absent"):
        args = message.content.split(" ")
        user = message.author
        userid = message.author.id
        if len(args) >= 3:
            # Crude date validator
            date = args[2].split("/")
            if int(date[0]) <= 12 and int(date[1]) <= 31:
                year = datetime.datetime.now().year
                args[2] += "/%s" % year
                await client.send_message(message.channel, "<@%s> says %s will be Absent on %s." % (userid, args[1], args[2]))
                reason = " ".join(args[3:]) if len(args) >= 4 else "Personal Reasons"
                att_table.put_item(
                    Item={
                        'discord_user': str(user),
                        'character_name': args[1],
                        'status': "Absent",
                        'date': args[2],
                        'reason': reason,
                        'active': True
                    }
                )
            else:
                await client.send_message(message.channel, "Invalid Date format. Please use MM/DD for date")

    # Command for viewing and saving a character to a discord user
    if message.content.lower().startswith("!character"):
        args = message.content.split(" ")
        user = message.author
        userid = message.author.id
        # Save character to discord user that initiated command
        # !character save <character name> <server name>
        # Allows each discord user to have multiple characters
        if args[1].lower() == "save":
            if len(args) == 4 and len(args[2]) <= 12:
                await client.send_message(message.channel, "Saving %s-%s to user <@%s>." % (args[2], args[3], userid))
                char_table.put_item(
                    Item={
                        'discord_user': str(user),
                        'character_name': args[2],
                        'character_server': args[3]
                    }
                )
            else:
                await client.send_message(message.channel, "Invalid Command Format. !character save <character name> <server-server>")
                return

        # View characters currently saved to discord user that initiated command
        # !character view
        if args[1].lower() == "view":
            if len(args) == 2:
                await client.send_message(message.channel, "Viewing characters for user <@%s>." % userid)
                response = char_table.query(
                    KeyConditionExpression=Key('discord_user').eq(str(user))
                )
                reply = "```++++++++++++++++++++++++++++++++++++++\n" \
                        "+ Character    + Server              +\n" \
                        "+------------------------------------+\n"
                for items in response['Items']:
                    character = "{:<12}".format(items["character_name"])
                    server = "{:<19}".format(items["character_server"])
                    reply += ("+ %s + %s +\n" % (character, server))
                reply += "++++++++++++++++++++++++++++++++++++++```"
                await client.send_message(message.channel, reply)
            else:
                await client.send_message(message.channel, "Invalid Command Format. !character view")
                return

    if message.content.lower().startswith("!count"):
        if message.author.id == "208298739679494144" or "430057708759023626" in [role.id for role in message.author.roles]:
            response = att_table.scan(
                FilterExpression=Attr('status').eq("Absent") & Attr('active').contains(True)
            )
            attendance = {}
            reply = "```++++++++++++++++++++++++++++++++++++++\n" \
                    "+ Character    + Number of Absences  +\n" \
                    "+------------------------------------+\n"
            for absence in response["Items"]:
                character = absence["character_name"]
                if character not in attendance:
                    attendance[character] = 0
                attendance[character] += 1
            for character, count in attendance.items():
                reply += "+ %s + %s +\n" % ("{:<12}".format(character), "{:<19}".format(count))
            reply += "++++++++++++++++++++++++++++++++++++++```"
            await client.send_message(message.channel, reply)

    # TODO Reset command to remove attendance
    # TODO Timed message reminding of absences?



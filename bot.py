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
                "!rfdattend <late/absent> <MM/DD> <character> <reason>\n" \
                "!rfdattend reset <MM/DD/all (officer only)> <character>\n" \
                "!rfdattend view <MM/DD>\n" \
                "!rfdattend count (officer only)\n" \
                "(Disabled)!rfdcharacter save <character name> <server-server>\n" \
                "(Disabled)!rfdcharacter view\n" \
                "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++```"
        await client.send_message(message.channel, reply)

    if message.content.lower().startswith("!rfdattendance") or message.content.lower().startswith("!rfdattend") or message.content.lower().startswith("!attend") \
            or message.content.lower().startswith("!attendance"):
        args = message.content.split(" ")
        user = message.author
        userid = message.author.id
        if len(args) == 2:
            # !rfdattend count
            if args[1].lower() == 'count':
                if message.author.id == "208298739679494144" or "430057708759023626" in [role.id for role in message.author.roles]:
                    response = att_table.scan(
                        FilterExpression=Attr('status').contains("absent") & Attr('active').eq(True)
                    )
                    print(response["Items"])
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
        if len(args) >= 3:
            # !rfdattend reset
            if args[1].lower() == "reset":
                # !rfdattend reset all
                if len(args[2]) == 1 and args[2].lower() == "all":
                    if message.author.id == "208298739679494144" or "430057708759023626" in [role.id for role in message.author.roles]:
                        response = att_table.scan()
                        for item in response["Items"]:
                            char_name = item["character_name"]
                            reason = item["reason"]
                            discord_user = item["discord_user"]
                            att_date = item["date"]
                            status = item["status"]

                            att_table.put_item(
                                Item={
                                    'discord_user': discord_user,
                                    'character_name': char_name,
                                    'status': status,
                                    'date': att_date,
                                    'reason': reason,
                                    'active': False
                                }
                            )
                        await client.send_message(message.channel, "Attendance Reset")

                    else:
                        print("You do not have permission to run this command")
                # !rfdattend reset <MM/DD> <character>
                if len(args[2]) > 1 and int(args[2][0]) <= 12 and int(args[2][1]) <= 31:
                    print("Reset Specific Date")
                    print(args[2])
                    print(args[3])
                    response = att_table.scan(
                        FilterExpression=Attr("date").contains(args[2]) & Attr("character_name").eq(args[3])
                    )
                    print(response["Items"])
                    for item in response["Items"]:
                        char_name = item["character_name"]
                        reason = item["reason"]
                        discord_user = item["discord_user"]
                        att_date = item["date"]
                        status = item["status"]

                        att_table.put_item(
                            Item={
                                'discord_user': discord_user,
                                'character_name': char_name,
                                'status': status,
                                'date': att_date,
                                'reason': reason,
                                'active': False
                            }
                        )
                        await client.send_message(message.channel, "Attendance Reset for %s on %s" % (char_name, att_date))
            # !rfdattend view <MM/DD>
            if args[1].lower() == "view":
                date = args[2].split("/")
                if int(date[0]) <= 12 and int(date[1]) <= 31:
                    year = datetime.datetime.now().year
                    args[2] += "/%s" % year
                    response = att_table.scan(
                        FilterExpression=Attr('date').eq(args[2]) & Attr('active').eq(True)
                    )
                    print(response["Items"])
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
            # !rfdattend <late/absent> <MM/DD> <character> <reason>
            if args[1].lower() == "late" or args[1].lower() == "absent":
                # Crude date validator
                date = args[2].split("/")
                if int(date[0]) <= 12 and int(date[1]) <= 31:
                    year = datetime.datetime.now().year
                    args[2] += "/%s" % year
                    await client.send_message(message.channel, "<@%s> says %s will be %s on %s." % (userid, args[3], args[1], args[2]))
                    reason = " ".join(args[4:]) if len(args) >= 5 else "Personal Reasons"
                    # print(reason)
                    att_table.put_item(
                        Item={
                            'discord_user': str(user),
                            'character_name': args[3],
                            'status': args[1],
                            'date': args[2],
                            'reason': reason,
                            'active': True
                        }
                    )
                else:
                    await client.send_message(message.channel, "Invalid Date format. Please use MM/DD for date")

    # Command for viewing and saving a character to a discord user
    # if message.content.lower().startswith("!rfdcharacter"):
    #     args = message.content.split(" ")
    #     user = message.author
    #     userid = message.author.id
    #     # Save character to discord user that initiated command
    #     # !character save <character name> <server name>
    #     # Allows each discord user to have multiple characters
    #     if args[1].lower() == "save":
    #         if len(args) == 4 and len(args[2]) <= 12:
    #             await client.send_message(message.channel, "Saving %s-%s to user <@%s>." % (args[2], args[3], userid))
    #             char_table.put_item(
    #                 Item={
    #                     'discord_user': str(user),
    #                     'character_name': args[2],
    #                     'character_server': args[3]
    #                 }
    #             )
    #         else:
    #             await client.send_message(message.channel, "Invalid Command Format. !character save <character name> <server-server>")
    #             return
    #
    #     # View characters currently saved to discord user that initiated command
    #     # !character view
    #     if args[1].lower() == "view":
    #         if len(args) == 2:
    #             await client.send_message(message.channel, "Viewing characters for user <@%s>." % userid)
    #             response = char_table.query(
    #                 KeyConditionExpression=Key('discord_user').eq(str(user))
    #             )
    #             reply = "```++++++++++++++++++++++++++++++++++++++\n" \
    #                     "+ Character    + Server              +\n" \
    #                     "+------------------------------------+\n"
    #             for items in response['Items']:
    #                 character = "{:<12}".format(items["character_name"])
    #                 server = "{:<19}".format(items["character_server"])
    #                 reply += ("+ %s + %s +\n" % (character, server))
    #             reply += "++++++++++++++++++++++++++++++++++++++```"
    #             await client.send_message(message.channel, reply)
    #         else:
    #             await client.send_message(message.channel, "Invalid Command Format. !character view")
    #             return


import json
from channels.generic.websocket import AsyncWebsocketConsumer

# Pushes order events to the kitchen display screen (one shared group).
class KitchenConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]

        # Only logged-in users may connect.
        if not user.is_authenticated:
            await self.close()
            return

        # Kitchen group: everyone connected here gets the same broadcasts.
        await self.channel_layer.group_add("kitchen", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("kitchen", self.channel_name)

    async def kitchen_event(self, event):
        # Relay the event payload down to the browser.
        await self.send(text_data=json.dumps(event["data"]))

import json
from channels.generic.websocket import AsyncWebsocketConsumer

# Pushes live updates for a single table's order (waiter screen).
class TableOrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]

        # Only logged-in users may connect.
        if not user.is_authenticated:
            await self.close()
            return

        self.zone = self.scope["url_route"]["kwargs"]["zone"]
        self.table = self.scope["url_route"]["kwargs"]["table"]

        # One group per table, so updates only reach that table's screen.
        self.group_name = f"table_{self.zone}_{self.table}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connected",
            "zone": self.zone,
            "table": self.table
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def table_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

import json
from channels.generic.websocket import AsyncWebsocketConsumer

# Pushes live updates for the tables overview screen (all tables at once).
class TablesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]

        # Only logged-in users may connect.
        if not user.is_authenticated:
            await self.close()
            return

        self.group_name = "tables"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({"type":"connected","scope":"tables"}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def tables_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

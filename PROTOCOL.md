# MemberMatters Access Device Protocol (MMADP)

This file briefly documents the MemberMatters Access Device Protocol and how it works.

## Auto discovery

> Due to an unresolved issue, mDNS lookups are currently not functioning correctly in our firmware or test network. Until this is resolved, auto discovery is subject to change.

The MemberMatters server broadcasts an mDNS name of `membermatters.local` and runs a websocket server available at `/ws/access` on port `80` (or `443` if SSL is configured) at this address (e.g. `ws://membermatters.local:80/ws/access`). A device that implements MMADP should attempt to resolve this mDNS address and connect to the websocket server.

## Packet Structure

Each packet is a JSON string with the following format.

```json
{
  "version": 1,
  "token": "device_token",
  "uuid": "uuidv4",
  "reply": "uuidv4", // optional
  "command": "<COMMAND>",
  "payload": {...}
}
```

## Packets

The name of each packet should be used as the `command` attribute above, and the payload as the `payload` attribute. Each packet should contain a `uuidv4` string that can be used to acknowledge it. Each device is assigned a token the first time it is "authorised" and this token must be included in any subsequent request. The `reply` attribute is optional and should only be included if it's a direct reply to the specified packet.

### hello (to server)

This must be the first packet sent to a server after connecting.

**Command:** `hello`

**Payload:**

```json
{
    "serial": "string",
    "class": "door" | "interlock"
}
```

- `serial` - this should be a unique, and unchanging string like the MAC address.
- `class` - the class of access device.

### device_authorised (from server)

Sent from the server when a device is authorised. The device should reply, and the server should try to send it a few times until it gets a reply.

**Command:** `device_authorised`

**Payload:**

```json
{
  "token": "token",
  "name": "name"
}
```

- `token` - this is a unique token used to authenticate the device. It should be saved and persisted between power cycles.
- `name` - the "friendly" name of the device, may be used as a DHCP hostname, etc.

### id_authorised_online (from server)

All id numbers contained in this payload should be authorised to access this device only when it is online. Up to 350 may be sent.

**Command:** `id_authorised_online`

**Payload:**

```json
[
    "id_number", ...
]
```

- `id_number` - an array of strings that represent authorised id numbers.

### id_authorised_offline (from server)

All id numbers contained in this payload should be authorised to access this device only when offline. Up to 350 may be sent.

**Command:** `id_authorised_offline`

**Payload:**

```json
[
    "id_number", ...
]
```

- `id_number` - an array of strings that represent authorised id numbers.

### id_authorised_admin (from server)

All id numbers contained in this payload should be authorised to access this device at all times, including when offline and during a maintenance lockout. Up to 350 may be sent.

**Command:** `id_authorised_admin`

**Payload:**

```json
[
    "id_number", ...
]
```

- `id_number` - an array of strings that represent authorised id numbers.

### door_access (to server)

The id_number that was requested access.

**Command:** `door_access`

**Payload:**

```json
{
    "id_number": "id_number",
    "time": "68439814631",
    "success": true | false,
    "method": "rfid" | "bluetooth"
}
```

- `id_number` - the id_number that requested access.
- `time` - unix timestamp of when the access was requested.
- `success` - if the access request was successful (granted).
- `method` - method used to request the access.

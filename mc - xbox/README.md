# MC Xbox

Browser-hosted prototype for the Minecraft-style project.

## Run

Double-click:

```text
run.bat
```

Or use Maven:

```bash
mvn spring-boot:run
```

Then open:

```text
http://localhost:5000
```

## What this first version does

- Starts a Spring Boot server on your laptop
- Serves a browser client
- Lets players join and move
- Syncs player state through REST
- Accepts keyboard input and basic gamepad movement
- Prints LAN URLs at startup

## Firewall

The app uses port `5000` and binds to `0.0.0.0` so other devices can reach it on the LAN.
If Windows Firewall asks, allow Java on `Private` networks.

## Next steps

- Add block place/break
- Add proper world chunks
- Add chat
- Add save/load
- Expand controller mappings for Xbox-style play

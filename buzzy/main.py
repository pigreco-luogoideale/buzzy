# Console per admin
# Responsive se diventa alta e stretta
# Server-driven

import time
import redis
import pickle
import asyncio
import uvicorn
from jinja2 import Template
from starlette.websockets import WebSocket
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles


player_template = Template(
    """\
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PiGame - {{ team_name }}</title>
    <style>
        html { height: 90%; }
        body {
            background-color: #666;
            height: 100%;
        }
        form {
            height: 100%;
            width: 100%;
            position: relative;
        }
        iframe {
            width: 100%;
            height: 1%;
            display: block;
            background: white;
            border: none;
            visibility: hidden;
        }
        .bottone {
            position: absolute;
            top: 5%;
            left: 5%;
            width: 90%;
            height: 90%;
            background: linear-gradient({{color}}, black 150%);
            border-radius: 50%;
            font-size: 4em;
            border: none;
            box-shadow: 0px 10px 10px black;
        }
        .bottone b {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 90%;
            height: 90%;
            margin: auto;
            background: linear-gradient(black -200%, {{color}});
            border-radius: 50%;
        }
        .bottone:active {
            background: linear-gradient(black -50%, {{color}});
        }
        .bottone:active b {
            background: linear-gradient({{color}}, black 150%);
        }
        button { outline: none; }
        button::-moz-focus-inner {
            outline: 0 !important;
            border: 0;
        }

        .bottone>b>i {
            mix-blend-mode: difference;
            color: white;
        }
    </style>
</head>
    <body>
        <iframe name="daframah" id="daframah"></iframe>
        <form action='/answer/{{ color }}/{{ team_name }}' target="daframah">
            <button class='bottone'><b><i>Press me!</i></b></button>
        </form>
    </body>
<html>
"""
)


registration_template = Template(
    """\
<!DOCTYPE HTML>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PiGioco</title>
    <style>
        body {
            background-color: black;
            color: white;
        }
    </style>
    <script type="text/javascript">
        function redirect(msg) {
            var color = document.getElementById("color").value.replace(/\s+/g, '');
            var name = document.getElementById("name").value.replace(/\s+/g, '');
            window.location.href = "/player/" + color + "/" + name;
        }
    </script>
</head>
<body>
    <h1>Registrations are open!</h1>
    <div><label>Team color: </label> <input id="color" placeholder="e.g. red, magenta, yellow"></div>
    <div><label>Team name: </label> <input id="name"> </div>
    <button onclick="redirect()">Start</button>
</body>
</html>
"""
)


server_template = Template(
    """\
<!DOCTYPE HTML>
<html>
<head>
    <style>
        html { height: 90%; }
        body {
            background-color: black;
            height: 100%;
        }
        div {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
        }
        #display {
            color: white;
            font-size: 5em;
        }
        #teams {
            width: 100%;
            height: 70px;
            font-size: 2em;
        }
    </style>
    <script type="text/javascript">
        function showText(msg) {
            document.getElementById("display").innerText = msg;
        }
        function countdown(wait_text, done_text, duration) {
            return function() {
                if (duration < 1) {
                    showText(done_text);
                    return;
                }
                var text = String(wait_text);
                text = text.replace("%%", String(duration));
                console.log("Writing", wait_text, typeof(wait_text));
                console.log(text, typeof(text));
                showText(text);
                setTimeout(countdown(wait_text, done_text, duration-1), 1000);
            };
        }
        function addPlayer(color, team_name) {
            var divIn = document.createElement("DIV");
            divIn.appendChild(document.createTextNode(team_name));
            divIn.id = "team_" + team_name;
            divIn.style.backgroundColor = color;
            divIn.style.width = '100%';

            var divOut = document.createElement("DIV");
            divOut.appendChild(divIn);
            divOut.style.backgroundColor = 'black';
            divOut.style.flexGrow = 1;
            divOut.style.justifyContent = 'left';

            document.getElementById("teams").appendChild(divOut);
            console.log("Registered team", color, team_name);
        }

        function animateCooldown(player, duration) {
            var start = null;
            var element = document.getElementById("team_" + player);

            function step(timestamp) {
                if (!start)
                    start = timestamp;
                var progress = Math.min(1, (timestamp - start) / duration);
                element.style.width = (progress * 100) + '%';
                if (progress <= 1)
                    window.requestAnimationFrame(step);
            }
            window.requestAnimationFrame(step);
        }

        function runWebsockets() {
            if ("WebSocket" in window) {
                var ws = new WebSocket("ws://{{wsaddr}}/ws/{{cooldown}}/{{register}}");
                ws.onopen = function() {
                    console.log("Websocket connection open");
                };
                ws.onmessage = function(e) { 
                    var data = JSON.parse(e.data);
                    console.log("Got data", data);

                    switch (data.command) {
                    case 'show':
                        showText(data.text);
                        break;
                    case 'player':
                        console.log("Adding player");
                        addPlayer(data.color, data.team_name);
                        break;
                    case 'countdown':
                        console.log("Countdown");
                        setTimeout(countdown(data.wait_text, data.done_text, data.duration), 1000);
                        break;
                    case 'buzz':
                        console.log("Buzzing");
                        if (data.siren || true) {
                            document.getElementById('siren').play();
                        }
                        showText(data.team_name);
                        if (data.cooldown)
                            animateCooldown(data.team_name, data.cooldown * 1000);
                        document.body.style.backgroundColor = data.color;
                        if (data.reset) {
                            setTimeout(function() {
                                showText(data.reset_text || "Get ready...");
                                document.body.style.backgroundColor = 'black';
                            }, data.reset * 1000);
                        }
                        break;
                    default:
                        console.log("Unknown command");
                        break;
                    }
                };
                ws.onclose = function() { 
                    console.log("Closing websocket connection");
                };
            } else {
                showText("Your browser might be too old. Use firefox!");
            }
        }
    </script>
</head>
<body onload="runWebsockets()">
    <div><span id="display">Connecting...</span></div>
    <div id='teams'></div>
    <audio id='siren' src="/static/sounds/buzz.ogg" type="audio/ogg">
        Your browser does not support the audio element.
    </audio> 
</body>
</html>
"""
)


app = Starlette()
app.mount("/static", StaticFiles(directory="static"))
red = redis.Redis(host="localhost", port=6379)


@app.route("/")
async def registration(request):
    return HTMLResponse(registration_template.render())


@app.route("/player/{color}/{team_name}")
async def client_page(request):
    color = request.path_params["color"]
    team_name = request.path_params["team_name"]
    return HTMLResponse(player_template.render(color=color, team_name=team_name))


@app.route("/answer/{color}/{team_name}")
async def answer_page(request):
    color = request.path_params["color"]
    team_name = request.path_params["team_name"]
    # Send to redis the player info
    red.publish("server", pickle.dumps((color, team_name)))
    return HTMLResponse("<div>Ok</div>")


# @app.route('/host/{cooldown}')
@app.route("/host/{cooldown}/{register}")
async def server_page(request):
    cooldown = request.path_params["cooldown"]
    register = request.path_params["register"]
    return HTMLResponse(
        server_template.render(
            cooldown=cooldown,
            register=register,
            address="http://pigioco.it",
            wsaddr=request.url.netloc,
        )
    )


# @app.websocket_route('/ws/{cooldown}')
@app.websocket_route("/ws/{cooldown}/{register}")
async def process_ws(websocket):
    await websocket.accept()
    # Build pubsub object
    p = red.pubsub()
    p.subscribe("server")

    # Manage teams
    join_duration = int(websocket.path_params["register"])
    join_time = time.time() + join_duration
    await websocket.send_json(
        {
            "command": "countdown",
            "duration": join_duration,
            "wait_text": "Waiting for players, %% seconds left.",
            "done_text": "Get ready!",
        }
    )
    # Or use command show to see unlimited text

    cooldown = int(websocket.path_params["cooldown"])
    # print("WEBSOCKET REQUEST", cooldown)
    cooldowns = {}

    # Time each player has to answer, in seconds
    answer_time = 3
    accepting_time = time.time()

    # Current team being displayed
    """
    case 'show':
        showText(data.text);
        break;
    case 'buzz':
        Parameters:
            data.siren, optional, bool (default to true)
            data.team_name, mandatory, str
            data.cooldown, mandatory, int (seconds)
            data.color, mandatory, str
            data.reset, optional, int (seconds)
            data.reset_text ["Get ready"]
    """

    # Process incoming messages
    while True:
        m = p.get_message()
        if m and m["type"] == "message":
            print("Got message at time", time.time())
            team = pickle.loads(m["data"])

            # When accepting teams, just add team to dict
            if time.time() < join_time:
                print("Still accepting...")
                if team not in cooldowns:
                    print("Accepted new player", team)
                    await websocket.send_json(
                        {"command": "player", "color": team[0], "team_name": team[1]}
                    )
                    cooldowns[team] = 0
                await asyncio.sleep(0.1)
                continue

            # We got a buzz message from a player
            # Are we accepting answers?
            if accepting_time >= time.time():
                print("We are not accepting answers yet, will do at", accepting_time)
                continue

            # Check if team was registered
            if team not in cooldowns:
                print("Unknown team", team)
                continue  # Discard message, invalid team

            # Ensure team is not on cooldown
            if time.time() < cooldowns[team]:
                print("Ignoring team on cooldown", team)
                continue

            # Ok, team can answer! Lock answers and set cooldown
            accepting_time = time.time() + answer_time
            cooldowns[team] = time.time() + cooldown

            await websocket.send_json(
                {
                    "command": "buzz",
                    "color": team[0],
                    "team_name": team[1],
                    "cooldown": cooldown,  # Player goes in cooldown
                    "reset": answer_time,  # Wait some time before resetting color
                }
            )
        await asyncio.sleep(0.1)
    await websocket.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug", reload=True)

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


player_template = Template("""\
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
""")


registration_template = Template("""\
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
""")


server_template = Template("""\
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
        function reset() {
            showText("Get ready...");
            document.body.style.backgroundColor = 'black';
            document.receiving = true;
        }
        function countdown(duration) {
            return function() {
                if (duration < 0) {
                    document.receiving = true;
                    showText("Get ready...");
                    return;
                }
                showText("Waiting players, " + duration + " seconds left. {{address}}");
                setTimeout(countdown(duration-1), 1000);
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

        function siren() {
            document.getElementById('siren').play();
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
                    showText("Waiting for players to join...");
                };
                ws.onmessage = function(e) { 
                    var data = JSON.parse(e.data);
                    console.log("Got data", data);

                    if (data.command == 'log') {
                        console.log(data.message);
                        return;
                    }

                    if (data.command == 'player') {
                        addPlayer(data.color, data.team_name);
                    }

                    if (data.command == 'join') {
                        document.receiving = false;
                        console.log("Setting timeout" + data.duration);
                        setTimeout(countdown(data.duration), 1000);
                        return;
                    }

                    if (!document.receiving) {
                        console.log("Cooldown ignore")
                        return;
                    }

                    document.receiving = false;
                    siren();
                    showText(data.team_name);
                    animateCooldown(data.team_name, data.cooldown * 1000);
                    document.body.style.backgroundColor = data.color;
                    setTimeout(reset, 2000);  // Reset color background
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
""")


app = Starlette()
app.mount('/static', StaticFiles(directory='static'))
red = redis.Redis(host='localhost', port=6379)


@app.route('/')
async def registration(request):
    return HTMLResponse(registration_template.render())


@app.route('/player/{color}/{team_name}')
async def client_page(request):
    color = request.path_params['color']
    team_name = request.path_params['team_name']
    return HTMLResponse(player_template.render(color=color,
                                               team_name=team_name))


@app.route('/answer/{color}/{team_name}')
async def answer_page(request):
    color = request.path_params['color']
    team_name = request.path_params['team_name']
    # Send to redis the player info
    red.publish('server', pickle.dumps((color, team_name)))
    return HTMLResponse('<div>Ok</div>')


@app.route('/host/{cooldown}')
@app.route('/host/{cooldown}/{register}')
async def server_page(request):
    cooldown = request.path_params['cooldown']
    register = request.path_params.get('register', 123)
    return HTMLResponse(server_template.render(cooldown=cooldown,
                                               register=register,
                                               address='http://pigioco',
                                               wsaddr=request.url.netloc))


@app.websocket_route('/ws/{cooldown}/{register}')
async def process_ws(websocket):
    await websocket.accept()
    # Build pubsub object
    p = red.pubsub()
    p.subscribe('server')

    # Manage teams
    accepting_duration = int(websocket.path_params['register'])
    accepting_time = time.time() + accepting_duration
    await websocket.send_json({
        'command': 'join',
        'duration': accepting_duration,
    })

    cooldown = int(websocket.path_params['cooldown'])
    # print("WEBSOCKET REQUEST", cooldown)
    cooldowns = {}


    # Current team being displayed

    # Process incoming messages
    while True:
        m = p.get_message()
        if m and m['type'] == 'message':
            team = pickle.loads(m['data'])

            # When accepting teams, just add team to dict
            if time.time() < accepting_time:
                print("Still accepting...")
                if team not in cooldowns:
                    await websocket.send_json({
                        'command': 'player',
                        'color': team[0],
                        'team_name': team[1],
                    })
                    cooldowns[team] = 0
                await asyncio.sleep(0.1)
                continue

            # Check if team is valid
            if team not in cooldowns:
                continue # Discard message, invalid team

            # Check cooldown
            if time.time() < cooldowns[team]:
                print("Ignoring team on cooldown", team)
                continue

            cooldowns[team] = time.time() + cooldown

            await websocket.send_json({
                'command': 'answer',
                'color': team[0],
                'team_name': team[1],
                'cooldown': cooldown,
            })
        await asyncio.sleep(0.1)
    await websocket.close()


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='debug', reload=True)

Using a flask server to host the server locally, I then use ngrok to make it exposed to the public.
From there, somehow get bootloader.ps1 to get run on the victims machine.
It connects to the c2 server specified in health.ps1, which should be the ngrok hostname.
127.0.0.1:5000 has the interface for sending commands to whatever victim youve infected.

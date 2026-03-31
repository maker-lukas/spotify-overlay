const clients = workspace.windowList();
for (let i = 0; i < clients.length; i++) {
    if (clients[i].caption === "Spotify Overlay") {
        clients[i].keepAbove = true;
        clients[i].skipTaskbar = true;
    }
}

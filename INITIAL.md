## FEATURE:

Revise our React based web app frontend to utilize React 19 and React best practices. The frontend will connect our backend's current functionaltiy to a user interface. This includes discovery processing, document processing via BOX folder-id, and outline and motion draft generation. Users will be able to choose their case on the sidebar to ensure they are working on the correct case and documents do not get mixed between cases. The primary feature for this frontend implementation is to have a working websocket connection to our backend as our current implementation does not work and times out. This includes updating any backends that were currently made with Gunicorn to a more suitable python backend to handle async nature of websockets

## EXAMPLES:

`examples/CLAUDE-react.md`: claude instructions on how to build with React. Similar to our current CLAUDE.md file, but generic and tailed towards React applications.

## DOCUMENTATION:

url: https://react.dev/reference/react
why: React documentation

url: https://python-socketio.readthedocs.io/en/stable/api.html
why: SocketIO documentation

file: CLAUDE.md
why: rules for project strucutre and testing

mcp: Context7 MCP Server
why: Use to look up additional documentation by library name

file: docker-compose.yml
why: docker compose file for local development with tech stack and full services

## OTHER CONSIDERATIONS:

Make sure .env variables are set properly and included in the correct folders
Ensure project is scalable to handle multiple cases from multiple law firms
Make adjustments as required if current backend tasks do not work well with the frontend, however, ensure functionaltiy remains the same. 
Ensure frontend is workable with our current tech stack
Ensure python start_services --profile cpu command works with new implementation
Caddy serves as our reverse proxy

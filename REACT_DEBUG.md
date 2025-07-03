## FEATURE:

When connecting the Clerk frontend on localhost:8010, i get the following console errors:

  index-BtLVjO7a.js:258 Auth disabled - using development auth service
  index-BtLVjO7a.js:258 Connecting to WebSocket: http://localhost:8000
  index-BtLVjO7a.js:258 WebSocket path: /ws/socket.io/
  index-BtLVjO7a.js:258 Error fetching cases: TypeError: m.replace is not a function
      at index-BtLVjO7a.js:258:131186
      at Array.map (<anonymous>)
      at d (index-BtLVjO7a.js:258:131150)
  d @ index-BtLVjO7a.js:258
  index-BtLVjO7a.js:258 WebSocket connection error: timeout
  (anonymous) @ index-BtLVjO7a.js:258
  index-BtLVjO7a.js:258 Attempting to reconnect in 1640.1075260517378ms...
  index-BtLVjO7a.js:258 WebSocket connection to
  'ws://localhost:8000/ws/socket.io/?EIO=4&transport=websocket' failed: WebSocket is closed before the
  connection is established.
  doClose @ index-BtLVjO7a.js:258
  index-BtLVjO7a.js:258 Connecting to WebSocket: http://localhost:8000
  index-BtLVjO7a.js:258 WebSocket path: /ws/socket.io/
  index-BtLVjO7a.js:258 WebSocket connection to
  'ws://localhost:8000/ws/socket.io/?EIO=4&transport=websocket' failed:
  createSocket @ index-BtLVjO7a.js:258
  index-BtLVjO7a.js:258 WebSocket connection error: websocket error
  (anonymous) @ index-BtLVjO7a.js:258
  index-BtLVjO7a.js:258 Attempting to reconnect in 1035.1175650564737ms...
  index-BtLVjO7a.js:258 Connecting to WebSocket: http://localhost:8000
  index-BtLVjO7a.js:258 WebSocket path: /ws/socket.io/
  index-BtLVjO7a.js:258 WebSocket connection to
  'ws://localhost:8000/ws/socket.io/?EIO=4&transport=websocket' failed:
  createSocket @ index-BtLVjO7a.js:258
  doOpen @ index-BtLVjO7a.js:258
  open @ index-BtLVjO7a.js:258
  _open @ index-BtLVjO7a.js:258
  Xs @ index-BtLVjO7a.js:258
  One @ index-BtLVjO7a.js:258
  $ne @ index-BtLVjO7a.js:258
  open @ index-BtLVjO7a.js:258
  o0 @ index-BtLVjO7a.js:258
  Wf @ index-BtLVjO7a.js:258
  l @ index-BtLVjO7a.js:258
  (anonymous) @ index-BtLVjO7a.js:258
  index-BtLVjO7a.js:258 WebSocket connection error: websocket error
  (anonymous) @ index-BtLVjO7a.js:258
  cn.emit @ index-BtLVjO7a.js:258
  onerror @ index-BtLVjO7a.js:258
  cn.emit @ index-BtLVjO7a.js:258
  s @ index-BtLVjO7a.js:258
  cn.emit @ index-BtLVjO7a.js:258
  _onError @ index-BtLVjO7a.js:258
  cn.emit @ index-BtLVjO7a.js:258
  onError @ index-BtLVjO7a.js:258
  ws.onerror @ index-BtLVjO7a.js:258
  index-BtLVjO7a.js:258 Attempting to reconnect in 1106.8156587342642ms...
  index-BtLVjO7a.js:258 Connecting to WebSocket: http://localhost:8000
  index-BtLVjO7a.js:258 WebSocket path: /ws/socket.io/
  index-BtLVjO7a.js:258 WebSocket connection to
  'ws://localhost:8000/ws/socket.io/?EIO=4&transport=websocket' failed:
  createSocket @ index-BtLVjO7a.js:258
  doOpen @ index-BtLVjO7a.js:258
  open @ index-BtLVjO7a.js:258
  _open @ index-BtLVjO7a.js:258
  Xs @ index-BtLVjO7a.js:258
  One @ index-BtLVjO7a.js:258
  $ne @ index-BtLVjO7a.js:258
  open @ index-BtLVjO7a.js:258
  o0 @ index-BtLVjO7a.js:258
  Wf @ index-BtLVjO7a.js:258
  l @ index-BtLVjO7a.js:258
  (anonymous) @ index-BtLVjO7a.js:258
  index-BtLVjO7a.js:258 WebSocket connection error: websocket error
  (anonymous) @ index-BtLVjO7a.js:258
  cn.emit @ index-BtLVjO7a.js:258
  onerror @ index-BtLVjO7a.js:258
  cn.emit @ index-BtLVjO7a.js:258
  s @ index-BtLVjO7a.js:258
  cn.emit @ index-BtLVjO7a.js:258
  _onError @ index-BtLVjO7a.js:258
  cn.emit @ index-BtLVjO7a.js:258
  onError @ index-BtLVjO7a.js:258
  ws.onerror @ index-BtLVjO7a.js:258
  index-BtLVjO7a.js:258 Attempting to reconnect in 1732.5012274669198ms...
  index-BtLVjO7a.js:258 Connecting to WebSocket: http://localhost:8000
  index-BtLVjO7a.js:258 WebSocket path: /ws/socket.io/


  The actual website says: m.replace is not a function

Ascertain the issue, research it, and provide a fix to this problem to ensure
   a stable connection. Use context7 if needed to research documentation.


## EXAMPLES:

`examples/CLAUDE-react.md`: claude instructions on how to build with React. Similar to our current CLAUDE.md file, but tailored towards React applications. Pay close attention to the idea of validating inputs early to "fail fast" and throw errors immediately.

## DOCUMENTATION:

url: https://react.dev/reference/react
why: React documentation

url: https://python-socketio.readthedocs.io/en/stable/api.html
why: SocketIO documentation

url: https://socket.io/how-to/use-with-react
why: How to use socketio with react

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

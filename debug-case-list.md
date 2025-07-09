## FEATURE:

When building the full tech stack from start_services_with_postgres.py --profile cpu, I can open the clerk frontend on localhost:8010. I can click "Add Case", then input the fields, and click create case. It looks like the case gets added to the database, but I get errors in the console. You task is to thoroughly research this error and provide a comprensive fix that does not break the current tech stack. 

## EXAMPLES:

Errors related to this error:

    DevTools Console
    index-6AoxRHbA.js:256 Auth disabled - using development auth service
    index-6AoxRHbA.js:256 Connecting to WebSocket: http://localhost:8010
    index-6AoxRHbA.js:256 WebSocket path: /ws/socket.io/
    cases:1 
                
                
            Failed to load resource: the server responded with a status of 401 (Unauthorized)
    index-6AoxRHbA.js:256 Error fetching cases: Error: Failed to fetch cases
        at f (index-6AoxRHbA.js:256:105814)
    f @ index-6AoxRHbA.js:256
    auth.service.dev-CYHC0NYg.js:1 Dev auth initialized with mock tokens
    index-6AoxRHbA.js:256 Received connected event from server: Object
    index-6AoxRHbA.js:256 WebSocket connected
    index-6AoxRHbA.js:256 WebSocket event handlers registered
    index-6AoxRHbA.js:256 
                
                
            GET http://localhost:8010/api/cases 401 (Unauthorized)
    f @ index-6AoxRHbA.js:256
    (anonymous) @ index-6AoxRHbA.js:256
    await in (anonymous)
    p @ index-6AoxRHbA.js:256
    (anonymous) @ index-6AoxRHbA.js:256
    await in (anonymous)
    AM @ index-6AoxRHbA.js:37
    LM @ index-6AoxRHbA.js:37
    FM @ index-6AoxRHbA.js:37
    Dx @ index-6AoxRHbA.js:37
    Uk @ index-6AoxRHbA.js:37
    (anonymous) @ index-6AoxRHbA.js:37
    Uy @ index-6AoxRHbA.js:40
    hk @ index-6AoxRHbA.js:37
    ym @ index-6AoxRHbA.js:37
    yy @ index-6AoxRHbA.js:37
    e2 @ index-6AoxRHbA.js:37
    index-6AoxRHbA.js:256 Error fetching cases: Error: Failed to fetch cases
        at f (index-6AoxRHbA.js:256:105814)
        at async index-6AoxRHbA.js:256:136545
        at async p (index-6AoxRHbA.js:256:138412)
        at async index-6AoxRHbA.js:256:131538
    f @ index-6AoxRHbA.js:256
    await in f
    (anonymous) @ index-6AoxRHbA.js:256
    await in (anonymous)
    p @ index-6AoxRHbA.js:256
    (anonymous) @ index-6AoxRHbA.js:256
    await in (anonymous)
    AM @ index-6AoxRHbA.js:37
    LM @ index-6AoxRHbA.js:37
    FM @ index-6AoxRHbA.js:37
    Dx @ index-6AoxRHbA.js:37
    Uk @ index-6AoxRHbA.js:37
    (anonymous) @ index-6AoxRHbA.js:37
    Uy @ index-6AoxRHbA.js:40
    hk @ index-6AoxRHbA.js:37
    ym @ index-6AoxRHbA.js:37
    yy @ index-6AoxRHbA.js:37
    e2 @ index-6AoxRHbA.js:37
    dashboard:1 Blocked aria-hidden on an element because its descendant retained focus. The focus must not be hidden from assistive technology users. Avoid using aria-hidden on a focused element or its ancestor. Consider using the inert attribute instead, which will also prevent focus. For more details, see the aria-hidden section of the WAI-ARIA specification at https://w3c.github.io/aria/#aria-hidden.
    Element with focus: <button.MuiButtonBase-root MuiButton-root MuiButton-outlined MuiButton-outlinedPrimary MuiButton-sizeSmall MuiButton-outlinedSizeSmall MuiButton-colorPrimary MuiButton-fullWidth MuiButton-root MuiButton-outlined MuiButton-outlinedPrimary MuiButton-sizeSmall MuiButton-outlinedSizeSmall MuiButton-colorPrimary MuiButton-fullWidth css-173u4yx>
    Ancestor with aria-hidden: <div#root> <div id=​"root">​…​</div>​
    index-6AoxRHbA.js:256 
                
                
            GET http://localhost:8010/api/cases 401 (Unauthorized)
    f @ index-6AoxRHbA.js:256
    d @ index-6AoxRHbA.js:256
    p @ index-6AoxRHbA.js:256
    await in p
    (anonymous) @ index-6AoxRHbA.js:256
    await in (anonymous)
    AM @ index-6AoxRHbA.js:37
    LM @ index-6AoxRHbA.js:37
    FM @ index-6AoxRHbA.js:37
    Dx @ index-6AoxRHbA.js:37
    Uk @ index-6AoxRHbA.js:37
    (anonymous) @ index-6AoxRHbA.js:37
    Uy @ index-6AoxRHbA.js:40
    hk @ index-6AoxRHbA.js:37
    ym @ index-6AoxRHbA.js:37
    yy @ index-6AoxRHbA.js:37
    e2 @ index-6AoxRHbA.js:37
    index-6AoxRHbA.js:256 Error fetching cases: Error: Failed to fetch cases
        at f (index-6AoxRHbA.js:256:105814)
        at async d (index-6AoxRHbA.js:256:142793)
    f @ index-6AoxRHbA.js:256
    await in f
    d @ index-6AoxRHbA.js:256
    p @ index-6AoxRHbA.js:256
    await in p
    (anonymous) @ index-6AoxRHbA.js:256
    await in (anonymous)
    AM @ index-6AoxRHbA.js:37
    LM @ index-6AoxRHbA.js:37
    FM @ index-6AoxRHbA.js:37
    Dx @ index-6AoxRHbA.js:37
    Uk @ index-6AoxRHbA.js:37
    (anonymous) @ index-6AoxRHbA.js:37
    Uy @ index-6AoxRHbA.js:40
    hk @ index-6AoxRHbA.js:37
    ym @ index-6AoxRHbA.js:37
    yy @ index-6AoxRHbA.js:37
    e2 @ index-6AoxRHbA.js:37
    index-6AoxRHbA.js:256 Switching from null to test_case_v_demo_case_c5324fb6
    index-6AoxRHbA.js:256 Selected case: test_case_v_demo_case_c5324fb6
    index-6AoxRHbA.js:256 WebSocket case mismatch. Active: test_case_v_demo_case_c5324fb6, Subscribed: null
    index-6AoxRHbA.js:256 WebSocket case mismatch. Active: test_case_v_demo_case_c5324fb6, Subscribed: null
    index-6AoxRHbA.js:256 Subscribed to case: test_case_v_demo_case_c5324fb6
    index-6AoxRHbA.js:256 Already subscribed to case: test_case_v_demo_case_c5324fb6

    postgres Docker logs

    2025-07-06 00:19:50.692 UTC [1] LOG:  starting PostgreSQL 17.5 (Debian 17.5-1.pgdg120+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14) 12.2.0, 64-bit

    2025-07-06 00:19:50.697 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432

    2025-07-06 00:19:50.697 UTC [1] LOG:  listening on IPv6 address "::", port 5432

    2025-07-06 00:19:50.793 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"

    2025-07-06 00:19:50.877 UTC [29] LOG:  database system was shut down at 2025-07-06 00:00:58 UTC

    2025-07-06 00:19:51.008 UTC [1] LOG:  database system is ready to accept connections

    2025-07-06 00:24:57.715 UTC [27] LOG:  checkpoint starting: time

    2025-07-06 00:24:57.937 UTC [27] LOG:  checkpoint complete: wrote 5 buffers (0.0%); 0 WAL file(s) added, 0 removed, 0 recycled; write=0.209 s, sync=0.004 s, total=0.223 s; sync files=3, longest=0.003 s, average=0.002 s; distance=14 kB, estimate=14 kB; lsn=0/1A54588, redo lsn=0/1A54530

    2025-07-06 01:41:42.203 UTC [12559] ERROR:  column users.is_admin does not exist at character 100

    2025-07-06 01:41:42.203 UTC [12559] HINT:  Perhaps you meant to reference the column "users.admin".

    2025-07-06 01:41:42.203 UTC [12559] STATEMENT:  SELECT users.id, users.email, users.password_hash, users.name, users.law_firm_id, users.is_active, users.is_admin, users.last_login, users.created_at, users.updated_at 

        FROM users 

        WHERE users.id = $1::VARCHAR

    2025-07-06 01:43:53.556 UTC [12559] ERROR:  column users.last_login does not exist at character 116

    2025-07-06 01:43:53.556 UTC [12559] STATEMENT:  SELECT users.id, users.email, users.password_hash, users.name, users.law_firm_id, users.is_active, users.is_admin, users.last_login, users.created_at, users.updated_at 

        FROM users 

        WHERE users.id = $1::VARCHAR

    2025-07-06 01:47:10.865 UTC [27] LOG:  checkpoint starting: time

    2025-07-06 01:47:14.899 UTC [27] LOG:  checkpoint complete: wrote 41 buffers (0.3%); 0 WAL file(s) added, 0 removed, 0 recycled; write=4.013 s, sync=0.009 s, total=4.034 s; sync files=32, longest=0.004 s, average=0.001 s; distance=64 kB, estimate=64 kB; lsn=0/1A647C0, redo lsn=0/1A64768

    2025-07-06 01:52:20.139 UTC [27] LOG:  checkpoint starting: time

    2025-07-06 01:52:21.675 UTC [27] LOG:  checkpoint complete: wrote 16 buffers (0.1%); 0 WAL file(s) added, 0 removed, 0 recycled; write=1.505 s, sync=0.022 s, total=1.536 s; sync files=16, longest=0.019 s, average=0.002 s; distance=6 kB, estimate=58 kB; lsn=0/1A66178, redo lsn=0/1A660E8

    2025-07-06 01:57:29.993 UTC [27] LOG:  checkpoint starting: time

    2025-07-06 01:57:31.013 UTC [27] LOG:  checkpoint complete: wrote 11 buffers (0.1%); 0 WAL file(s) added, 0 removed, 0 recycled; write=1.004 s, sync=0.007 s, total=1.020 s; sync files=11, longest=0.004 s, average=0.001 s; distance=35 kB, estimate=56 kB; lsn=0/1A6F070, redo lsn=0/1A6F018

    2025-07-06 02:02:38.411 UTC [27] LOG:  checkpoint starting: time

    2025-07-06 02:02:39.941 UTC [27] LOG:  checkpoint complete: wrote 16 buffers (0.1%); 0 WAL file(s) added, 0 removed, 0 recycled; write=1.506 s, sync=0.005 s, total=1.530 s; sync files=16, longest=0.003 s, average=0.001 s; distance=12 kB, estimate=52 kB; lsn=0/1A72148, redo lsn=0/1A720F0

    DevTools Network tab
    GET /api/cases HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate, br, zstd
    Accept-Language: en-US,en;q=0.9
    Connection: keep-alive
    Host: localhost:8010
    Referer: http://localhost:8010/dashboard
    Sec-Fetch-Dest: empty
    Sec-Fetch-Mode: cors
    Sec-Fetch-Site: same-origin
    User-Agent: Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36
    sec-ch-ua: "Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"
    sec-ch-ua-mobile: ?1
    sec-ch-ua-platform: "Android"
    HTTP/1.1 401 Unauthorized
    Content-Length: 41
    Content-Type: application/json
    Date: Sun, 06 Jul 2025 02:02:19 GMT
    Server: uvicorn
    Via: 1.1 Caddy
    Www-Authenticate: Bearer
    f @ http://localhost:8010/assets/index-6AoxRHbA.js:256
    (anonymous) @ http://localhost:8010/assets/index-6AoxRHbA.js:256
    p @ http://localhost:8010/assets/index-6AoxRHbA.js:256
    (anonymous) @ http://localhost:8010/assets/index-6AoxRHbA.js:256
    AM @ http://localhost:8010/assets/index-6AoxRHbA.js:37
    LM @ http://localhost:8010/assets/index-6AoxRHbA.js:37
    FM @ http://localhost:8010/assets/index-6AoxRHbA.js:37
    Dx @ http://localhost:8010/assets/index-6AoxRHbA.js:37
    Uk @ http://localhost:8010/assets/index-6AoxRHbA.js:37
    (anonymous) @ http://localhost:8010/assets/index-6AoxRHbA.js:37
    Uy @ http://localhost:8010/assets/index-6AoxRHbA.js:40
    hk @ http://localhost:8010/assets/index-6AoxRHbA.js:37
    ym @ http://localhost:8010/assets/index-6AoxRHbA.js:37
    yy @ http://localhost:8010/assets/index-6AoxRHbA.js:37
    e2 @ http://localhost:8010/assets/index-6AoxRHbA.js:37


## DOCUMENTATION:

url: https://react.dev/reference/react
why: React documentation

url: https://python-socketio.readthedocs.io/en/stable/api.html
why: SocketIO documentation

url: https://www.postgresql.org/docs/17/index.html
why: Postgres documentation

file: CLAUDE.md
why: rules for project strucutre and testing

mcp: Context7 MCP Server
why: Use to look up additional documentation by library name (qdrant, for example)

mcp: Brave-search MCP Server
why: Use to search the web for information in your research

file: `start_services_with_postgres.py`
why: script to launch the full tech stack. Utilized with argument `--profile cpu`

## OTHER CONSIDERATIONS:

This error comes in the clerk frontend that is part of a larger tech stack. We launch this tech stack with the command `python start_services_with_postgres.py --profile cpu`. You must fully review this file, the related docker-compose files, and any other files that are part of the tech stack to ensure that the error is fixed without breaking the tech stack.

Always perform tests early and often. You do not need my input for tests, run them yourself.

The priority is to ensure all services inside the tech stack can communicate with each other. Being able to interact with the docker via a local terminal is not a priority. Ensure that internal communications are never broken.


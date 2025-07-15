## FEATURE:

The discovery processing feature is working as intended on the backend. However, the frontend is not receiving the events in real-time and the websocket times out constantly.

An overview of the processing flow is as follows:

1. User uploads pdf file(s) to the discovery processing page on the frontend and clicks "Start Processing"
2. The clerk backend takes that pdf file and determines document boundaries. Then each document is processed indivudally, extracting case facts and storing those in the case_facts database. In addition, the entire document is chunked and stored in the regular case database. This process repeats for every segment found.

What is not working is the frontend. After clicking "Start Processing", the frontend navigates to the Discovering processing screen but then just stays there. After about 30s, it times out until the document boundary process is complete, then it reconnects but nothing actually happens. What is supposed to happen is as follows:

1. After the boundary determines how many segments exist in the document, it creates a "tab" for each document along the top of the page for the end user to navigate to each document. Tabs are greyed out until that indivual segment is processed.
2. After the indidvidual segement is processed, the tab becomes clickable. clicking the tab shows the document in the PDF viewer and the facts extracted from that document in the fact review panel via fact cards.
3. The end user can then review the facts and edit them as needed. 

Your task is to review the full backend code for the discovery processing feature and determine why the frontend is not receiving the events in real-time and the websocket times out constantly.

## EXAMPLES:

[Provide and explain examples/code snips that an AI agent would use]

## DOCUMENTATION:

`discovery-processing.md`: an overview of the discovery processing feature. 
`Clerk\src\api\discovery_endpoints.py`: This file contains the endpoints for the discovery processing feature.
`Clerk\frontend\`: the full frontend code. You should review all relevant files for the discovery processing feature.
`Clerk\DISCOVERY_FRONTEND_IMPLEMENTATION.md`: an overview of the discovery processing frontend implementation. This may be outdated, so verify the code against this document but feel free to utilize any components that were created and aren't be used properly. 

## OTHER CONSIDERATIONS:

Do not use supabase for anything. qdrant is used for vector storage and postgres is used for database storage.
Run tests early and often. Only run tests from inside the docker environment and make sure to use the docker-compose.yml file to run the tests. The full startup script is `python start_services_with_postgres.py --profile cpu`, make sure you fully understand this script and the docker-compose.yml file

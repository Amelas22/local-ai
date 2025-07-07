## FEATURE:

We currently start our tech stack utilzing the command `python start_services_with_postgres.py --profile cpu`. The process first starts up supabase and then starts the packages in the tech stack. We have moved our backend of Clerk off of supabase and onto postgres due to repeated issues with supabase. Before I migrate the start up services off of supabase, I want to fully understand the process it currently undertakes. Here are the tasks I look to complete:

1. Review the `python start_services_with_postgres.py --profile cpu` script and review the related docker-compose files to understand the process of starting up supabase and the tech stack.
2. Thoroughly review the `/supabase/` directory to understand the process of starting up supabase and what services it performs.
3. Review our current codebase and determine what services currently still rely on supabase. 
4. Perform a review of these processes and decide how critical each service is to the tech stack. 
5. Use brave-search mcp to research alternatives to supabase and determine if any of them are a better fit for our tech stack.
6. Finally, if there are no alternatives that are better fit for our process, then I'm fine with continuing the supabase as it currently works. I'm just annoyed by it.
7. Finally, give a pro/con report and your recommendations. Again, I'm okay staying as is if that is the best solution. 

As mentioned before, we've migrated off of supabase for Clerk and are using postgres instead. We are not using supabase for any Clerk related services. However, the one thing I did like about supabase was it's visual endpoint that I could log into localhost:8000 or supabase.yourdomain.com to view the database and tables. I would like you to use brave-search to research alternatives so this feature can still exist inside our new postgres backend. This is seperate from the above pro/con analysis.

## EXAMPLES:

`/supabase`: supabase folder
`/Clerk`: clerk services folder
`python start_services_with_postgres.py --profile cpu`: start services with postgres

## DOCUMENTATION:

url: https://supabase.com/llms/python.txt
why: Supabase documentation

url: https://www.postgresql.org/docs/17/index.html
why: Postgres 17 documentation

file: CLAUDE.md
why: rules for project strucutre and testing

mcp: Context7 MCP Server
why: Use to look up additional documentation by library name (qdrant, for example)

mcp: Brave-search MCP Server
why: Use to search the web for information in your research

## OTHER CONSIDERATIONS:

All changes must still work with our current tech stack. Make sure you fully understand the `python start_services_with_postgres.py --profile cpu` script and related docker-compose files to ensure that any changes does not break any functionality.

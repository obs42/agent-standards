# Fresh-context handoff

An invocation requests the complete workflow: summarize, create a new task, and open it. Do not ask again whether to create the task. Follow an explicit document-only or other narrower request instead. Use the user's language.

## Prepare the handoff

Write a concise UTF-8 Markdown handoff to a uniquely named file in the OS temporary directory, outside the current workspace. Resolve and retain its absolute path. Aim for about 1,000-2,000 Chinese characters or 600-1,000 English words, expanding only for essential details. Do not copy the transcript, raw tool output, or abandoned investigations.

Capture:
- The current objective, the user's latest requirements, and the next session's requested focus (if supplied).
- Decisions and constraints that still apply, including the scope of existing authorization.
- Completed work, verification results, unresolved issues, and the next concrete actions.
- Current absolute workspace path, relevant project identity, and branch/worktree/uncommitted state when relevant. Check only what is needed to avoid a wrong checkout or stale claim.
- Absolute paths or URLs for relevant files, specs, plans, commits, and other artifacts. Reference existing material instead of duplicating it.
- Suggested skills, limited to those relevant to the next work; have the new agent read their instructions through available tools.

Exclude credentials and unnecessary personal information. Clearly separate observed facts from assumptions. Verify the saved file exists and is readable before creating the task.

## Create a task with a clean conversation

Use the Codex app's `create_thread` tool. Do not use `fork_thread` or `handoff_thread`: this workflow needs a new conversation containing only the short startup prompt and the handoff it reads.

Call `list_projects` before choosing a project. For this skill the user's preference is to continue directly in the same saved project, so select its returned project ID with `target.type = project` and `environment.type = local`. Check that the saved project's directory matches the current workspace; a different worktree or checkout may not include the current changes. If there is no matching saved project, use a projectless task and explicitly provide the source workspace path in its prompt. Do not silently switch branches, create another worktree, register a project, or copy files. For an existing projectless conversation, create another projectless task and include any source files by absolute path.

Omit model and thinking overrides unless the user explicitly requests them.

Before creating the task, obtain the current task's exact title using available task metadata (`list_threads` or `read_thread`) and retain it as the source title. Identify the calling task reliably; do not assume the first active task or another task in the same directory is the source. Copy the source title verbatim into `create_thread.title`, rather than inventing or summarizing a title. If the source already ends with the workflow's `（需要归档）` suffix, remove that trailing marker for the new task title. If the source cannot be identified reliably, ask only for the missing task identity/title before creation.

Once creation succeeds with a real `threadId`, use `set_thread_title` to ensure the new task has the exact intended title if creation normalized it. Then use `set_thread_title` with `threadId` omitted to rename the calling (old) task to its original title plus `（需要归档）`. Append this suffix only once. Do not mark the old task when creation fails or remains uncertain; for queued setup wait until the real task is confirmed. This is a title marker only: do not automatically archive the source task. A rename failure must not trigger duplicate task creation; report any incomplete rename.

The startup prompt must contain the absolute handoff path, the source workspace path, the next focus, and these instructions in the user's language:

> Read the handoff document first. This is a fresh task; use that document and relevant project files as your starting context. Do not load the old conversation or invoke handoff again. Briefly state the current objective, completed work, and next step to confirm that you read it. Then continue any clearly authorized unfinished work, verifying current file state before edits. If there is no pending authorized action, report readiness and wait for the user's next instruction. Read referenced files only as needed.

Do not paste the full conversation into the prompt. Do not send a second startup message after successful creation.

## Open and verify

Creation is asynchronous. If a real `threadId` is returned, use `navigate_to_codex_page` to show the new task, and use one bounded `wait_threads` call (up to 60 seconds) to check initial progress. A `clientThreadId` is not a `threadId`; resolve setup through available task tools before navigating or waiting. Do not recreate the task while setup is pending.

Report only confirmed results: whether the document was saved, the task created/opened, and whether it has confirmed reading. A pending read is not a completed handoff. Emit the required `::created-thread{threadId="..."}` or `::created-thread{clientThreadId="..."}` directive using the returned ID. Opening a task means navigating the Codex UI; do not claim a separate native OS window was opened unless a tool actually did so.

If creation is unavailable or fails, preserve the document and provide a short copyable startup prompt with its absolute path. If the result is uncertain, inspect task state before retrying to avoid duplicates. If opening fails after creation, report the created task rather than creating another one. Leave the source task intact and stop working on the transferred task here to avoid competing edits.
